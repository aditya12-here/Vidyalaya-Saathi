# backend/app/services/budget/cost_estimator.py
#
# Produces a default cost estimate for a problem when no admin-provided
# quote exists yet. Uses the same category-based approach as the reach
# sub-score in the Prioritization Engine (app/services/prioritization/
# scoring.py) — a base cost per category, scaled by a headcount/quantity
# parsed from `scale_estimate` for categories where cost genuinely scales
# with unit count (e.g. furniture), and adjusted by condition severity
# (a "Critical" issue typically means more extensive, costlier repair work
# than the same category at "Fair").
#
# All figures are illustrative placeholder defaults in INR, intended to be
# tuned per-deployment (or overridden per-problem by an admin via the API) —
# not sourced from any real costing database.

import re
from typing import Optional, Tuple
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.image import Problem
from app.models.budget import ProblemCostEstimate

# Flat baseline repair/replacement cost per category (INR), used when the
# category's cost doesn't meaningfully scale with a headcount/quantity.
CATEGORY_BASE_COST = {
    "Drinking Water": 30000.0,
    "Toilets": 60000.0,
    "Electricity": 40000.0,
    "Boundary/School Premises": 70000.0,
    "School Building": 150000.0,
    "Road/Access to School": 100000.0,
    "Playground": 40000.0,
    "Surrounding Area": 20000.0,
    "Classroom": 90000.0,
    "Other": 25000.0,
}
CATEGORY_BASE_COST_DEFAULT = 25000.0

# Categories where cost scales per-unit with a number extracted from
# `scale_estimate` (e.g. "Approximately 4 damaged desks" -> 4 * unit cost).
PER_UNIT_COST = {
    "Furniture": 1800.0,  # per damaged/missing item
}

CONDITION_COST_MULTIPLIER = {
    "critical": 1.5,
    "poor": 1.2,
    "fair": 1.0,
    "good": 0.5,
}
CONDITION_COST_MULTIPLIER_DEFAULT = 1.0


def _extract_headcount(scale_estimate: Optional[str]) -> Optional[int]:
    if not scale_estimate:
        return None
    match = re.search(r"\d+", scale_estimate)
    return int(match.group()) if match else None


def estimate_cost(problem: Problem) -> Tuple[float, str]:
    """Returns (estimated_cost, human_readable_note)."""
    category = problem.category
    condition_key = (problem.condition or "").strip().lower()
    multiplier = CONDITION_COST_MULTIPLIER.get(condition_key, CONDITION_COST_MULTIPLIER_DEFAULT)

    if category in PER_UNIT_COST:
        headcount = _extract_headcount(problem.scale_estimate)
        if headcount:
            base = headcount * PER_UNIT_COST[category]
            note = f"{headcount} unit(s) x Rs.{PER_UNIT_COST[category]:.0f}/unit ({category})"
        else:
            base = CATEGORY_BASE_COST.get(category, CATEGORY_BASE_COST_DEFAULT)
            note = f"Flat baseline for {category} (no unit count parsed from scale_estimate)"
    else:
        base = CATEGORY_BASE_COST.get(category, CATEGORY_BASE_COST_DEFAULT)
        note = f"Flat baseline for {category}"

    cost = round(base * multiplier, 2)
    note += f", x{multiplier} condition multiplier ({condition_key or 'unknown'})"
    return cost, note


async def _get_latest_estimate(db: AsyncSession, problem_id) -> Optional[ProblemCostEstimate]:
    result = await db.execute(
        select(ProblemCostEstimate).where(
            ProblemCostEstimate.problem_id == problem_id,
            ProblemCostEstimate.is_latest == True,  # noqa: E712
        )
    )
    return result.scalars().first()


async def ensure_cost_estimates(
    db: AsyncSession,
    school_id: str,
    problems,
    force_refresh: bool = False,
) -> dict:
    """
    Ensures every problem in `problems` has a latest cost estimate. Problems
    that already have one are left untouched unless force_refresh=True (and
    even then, an existing ADMIN_OVERRIDE is never silently replaced by a
    heuristic — only missing estimates or prior HEURISTIC ones are refreshed).
    Returns {problem_id_str: estimated_cost} for every problem passed in.
    """
    result_map = {}
    for problem in problems:
        existing = await _get_latest_estimate(db, problem.problem_id)

        needs_new = existing is None or (
            force_refresh and existing.source == "HEURISTIC"
        )

        if not needs_new:
            result_map[str(problem.problem_id)] = existing.estimated_cost
            continue

        cost, note = estimate_cost(problem)

        if existing:
            existing.is_latest = False
            db.add(existing)

        new_estimate = ProblemCostEstimate(
            problem_id=problem.problem_id,
            school_id=school_id,
            estimated_cost=cost,
            source="HEURISTIC",
            notes=note,
            is_latest=True,
        )
        db.add(new_estimate)
        result_map[str(problem.problem_id)] = cost

    await db.commit()
    return result_map


async def set_manual_cost(
    db: AsyncSession,
    problem_id,
    school_id: str,
    cost: float,
    notes: Optional[str] = None,
    created_by: Optional[str] = None,
) -> ProblemCostEstimate:
    """Admin-provided real quote, supersedes any prior estimate for this problem."""
    existing = await _get_latest_estimate(db, problem_id)
    if existing:
        existing.is_latest = False
        db.add(existing)

    new_estimate = ProblemCostEstimate(
        problem_id=problem_id,
        school_id=school_id,
        estimated_cost=cost,
        source="ADMIN_OVERRIDE",
        notes=notes,
        is_latest=True,
        created_by=created_by,
    )
    db.add(new_estimate)
    await db.commit()
    await db.refresh(new_estimate)
    return new_estimate