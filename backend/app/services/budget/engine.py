# backend/app/services/budget/engine.py
#
# Orchestrates a full budget planning run for a school:
#   1. Fetch each eligible problem's LATEST priority score (from the
#      Prioritization Engine feature — requires that engine to have been
#      run at least once for this school).
#   2. Ensure every eligible problem has a cost estimate (auto-generates
#      heuristic ones for any that are missing).
#   3. Split into MANDATORY (safety_override=True) and OPTIONAL pools.
#      Fund all mandatory items first, off the top of the budget.
#   4. Run the 0/1 knapsack optimizer (optimizer.py) on the optional pool
#      with whatever budget remains.
#   5. Persist a BudgetPlan + BudgetPlanAllocation rows, return the summary.

from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.image import Problem
from app.models.prioritization import ProblemPriorityScore
from app.models.budget import BudgetPlan, BudgetPlanAllocation
from app.services.budget.cost_estimator import ensure_cost_estimates
from app.services.budget.optimizer import solve_knapsack, KnapsackItem
from app.services.prioritization.engine import (
    EXCLUDED_HUMAN_STATUSES,
    EXCLUDED_LIFECYCLE_STATUSES,
)

DEFAULT_GRANULARITY_FRACTION = 0.01  # 1% of budget ceiling
MIN_GRANULARITY = 100.0


async def _get_scored_eligible_problems(db: AsyncSession, school_id: str):
    """
    Problems for this school that are (a) not Rejected/Resolved/Closed, same
    eligibility rule as the Prioritization Engine, and (b) have a latest
    priority score already computed. Returns list of (Problem, ProblemPriorityScore).
    """
    result = await db.execute(
        select(Problem, ProblemPriorityScore)
        .join(ProblemPriorityScore, ProblemPriorityScore.problem_id == Problem.problem_id)
        .where(
            Problem.school_id == school_id,
            ProblemPriorityScore.is_latest == True,  # noqa: E712
        )
    )
    rows = result.all()
    return [
        (p, s) for (p, s) in rows
        if (p.human_status not in EXCLUDED_HUMAN_STATUSES)
        and ((p.lifecycle_status or "Identified") not in EXCLUDED_LIFECYCLE_STATUSES)
    ]


async def run_budget_plan(
    db: AsyncSession,
    school_id: str,
    budget_ceiling: float,
    granularity: Optional[float] = None,
    triggered_by: Optional[str] = "ADMIN",
) -> dict:
    if budget_ceiling <= 0:
        raise ValueError("budget_ceiling must be a positive number.")

    scored_problems = await _get_scored_eligible_problems(db, school_id)
    if not scored_problems:
        raise ValueError(
            f"No prioritized problems found for school_id={school_id!r}. "
            "Run POST /prioritization/school/{school_id}/run first."
        )

    problems_only = [p for (p, _s) in scored_problems]
    cost_map = await ensure_cost_estimates(db, school_id, problems_only)

    granularity = granularity or max(budget_ceiling * DEFAULT_GRANULARITY_FRACTION, MIN_GRANULARITY)

    mandatory_entries = []
    optional_entries = []
    for problem, score in scored_problems:
        cost = cost_map[str(problem.problem_id)]
        entry = {"problem": problem, "score_row": score, "cost": cost}
        if score.safety_override:
            mandatory_entries.append(entry)
        else:
            optional_entries.append(entry)

    mandatory_cost = round(sum(e["cost"] for e in mandatory_entries), 2)
    over_budget_on_mandatory = mandatory_cost > budget_ceiling
    remaining_budget = max(budget_ceiling - mandatory_cost, 0.0)

    optional_items = [
        KnapsackItem(problem_id=str(e["problem"].problem_id), cost=e["cost"], score=e["score_row"].total_score)
        for e in optional_entries
    ]
    knapsack_result = solve_knapsack(optional_items, remaining_budget, granularity)
    selected_optional_ids = {item.problem_id for item in knapsack_result.selected}

    total_priority_score_available = round(
        sum(e["score_row"].total_score for e in mandatory_entries)
        + sum(e["score_row"].total_score for e in optional_entries),
        2,
    )
    total_priority_score_covered = round(
        sum(e["score_row"].total_score for e in mandatory_entries) + knapsack_result.total_score, 2
    )
    coverage_pct = round(
        (total_priority_score_covered / total_priority_score_available * 100)
        if total_priority_score_available > 0 else 0.0,
        2,
    )
    optimized_cost = knapsack_result.total_cost
    total_spent = round(mandatory_cost + optimized_cost, 2)

    plan = BudgetPlan(
        school_id=school_id,
        budget_ceiling=budget_ceiling,
        granularity_used=granularity,
        mandatory_cost=mandatory_cost,
        optimized_cost=optimized_cost,
        total_spent=total_spent,
        over_budget_on_mandatory=over_budget_on_mandatory,
        total_priority_score_available=total_priority_score_available,
        total_priority_score_covered=total_priority_score_covered,
        coverage_pct=coverage_pct,
        triggered_by=triggered_by,
    )
    db.add(plan)
    await db.flush()

    allocations_out = []

    for e in mandatory_entries:
        alloc = BudgetPlanAllocation(
            plan_id=plan.plan_id,
            problem_id=e["problem"].problem_id,
            selected=True,
            selection_reason="MANDATORY_SAFETY",
            cost=e["cost"],
            priority_score=e["score_row"].total_score,
            score_per_currency_unit=(e["score_row"].total_score / e["cost"]) if e["cost"] > 0 else None,
        )
        db.add(alloc)
        allocations_out.append({
            "problem_id": str(e["problem"].problem_id),
            "title": e["problem"].title,
            "category": e["problem"].category,
            "cost": e["cost"],
            "priority_score": e["score_row"].total_score,
            "tier": e["score_row"].tier,
            "selected": True,
            "selection_reason": "MANDATORY_SAFETY",
        })

    for e in optional_entries:
        pid = str(e["problem"].problem_id)
        selected = pid in selected_optional_ids
        reason = "OPTIMIZED" if selected else "NOT_SELECTED"
        alloc = BudgetPlanAllocation(
            plan_id=plan.plan_id,
            problem_id=e["problem"].problem_id,
            selected=selected,
            selection_reason=reason,
            cost=e["cost"],
            priority_score=e["score_row"].total_score,
            score_per_currency_unit=(e["score_row"].total_score / e["cost"]) if e["cost"] > 0 else None,
        )
        db.add(alloc)
        allocations_out.append({
            "problem_id": pid,
            "title": e["problem"].title,
            "category": e["problem"].category,
            "cost": e["cost"],
            "priority_score": e["score_row"].total_score,
            "tier": e["score_row"].tier,
            "selected": selected,
            "selection_reason": reason,
        })

    await db.commit()
    await db.refresh(plan)

    allocations_out.sort(key=lambda a: (not a["selected"], -a["priority_score"]))

    return {
        "plan_id": str(plan.plan_id),
        "school_id": school_id,
        "budget_ceiling": budget_ceiling,
        "granularity_used": granularity,
        "mandatory_cost": mandatory_cost,
        "optimized_cost": optimized_cost,
        "total_spent": total_spent,
        "over_budget_on_mandatory": over_budget_on_mandatory,
        "total_priority_score_available": total_priority_score_available,
        "total_priority_score_covered": total_priority_score_covered,
        "coverage_pct": coverage_pct,
        "optimization_method": knapsack_result.method,
        "triggered_by": triggered_by,
        "created_at": plan.created_at.isoformat() if plan.created_at else None,
        "allocations": allocations_out,
    }