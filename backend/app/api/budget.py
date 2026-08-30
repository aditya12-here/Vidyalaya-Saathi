# backend/app/api/budget.py
#
# Endpoints:
#   POST /api/v1/budget/school/{school_id}/plan
#       -> runs the budget optimizer for a given budget_ceiling, persists
#          and returns the plan (mandatory + optimized selections)
#   GET  /api/v1/budget/school/{school_id}/plan/latest
#       -> the most recently computed plan, with problem titles joined in
#   GET  /api/v1/budget/school/{school_id}/plans
#       -> history of all plans run for this school
#   PUT  /api/v1/budget/cost/{problem_id}
#       -> admin sets/overrides a real cost quote for a problem
#   GET  /api/v1/budget/cost/{problem_id}
#       -> current cost estimate for a problem (heuristic or override)

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Optional
from pydantic import BaseModel, Field
import uuid

from app.database import get_db
from app.models.image import School, Problem
from app.models.budget import BudgetPlan, BudgetPlanAllocation, ProblemCostEstimate
from app.services.budget.engine import run_budget_plan
from app.services.budget.cost_estimator import set_manual_cost

router = APIRouter(prefix="/budget", tags=["budget"])


class BudgetPlanRequest(BaseModel):
    budget_ceiling: float = Field(..., gt=0)
    granularity: Optional[float] = Field(None, gt=0)
    triggered_by: Optional[str] = "ADMIN"


class CostOverrideRequest(BaseModel):
    school_id: str
    cost: float = Field(..., ge=0)
    notes: Optional[str] = None
    created_by: Optional[str] = None


async def _require_school(db: AsyncSession, school_id: str) -> School:
    school = await db.get(School, school_id)
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    return school


@router.post("/school/{school_id}/plan")
async def create_budget_plan(
    school_id: str,
    body: BudgetPlanRequest,
    db: AsyncSession = Depends(get_db),
):
    await _require_school(db, school_id)
    try:
        result = await run_budget_plan(
            db, school_id,
            budget_ceiling=body.budget_ceiling,
            granularity=body.granularity,
            triggered_by=body.triggered_by,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result


@router.get("/school/{school_id}/plan/latest")
async def get_latest_plan(school_id: str, db: AsyncSession = Depends(get_db)):
    await _require_school(db, school_id)

    plan_result = await db.execute(
        select(BudgetPlan)
        .where(BudgetPlan.school_id == school_id)
        .order_by(BudgetPlan.created_at.desc())
    )
    plan = plan_result.scalars().first()
    if not plan:
        return {
            "school_id": school_id,
            "message": "No budget plan yet. POST /budget/school/{school_id}/plan first.",
        }

    alloc_result = await db.execute(
        select(BudgetPlanAllocation, Problem)
        .join(Problem, Problem.problem_id == BudgetPlanAllocation.problem_id)
        .where(BudgetPlanAllocation.plan_id == plan.plan_id)
    )
    rows = alloc_result.all()
    rows.sort(key=lambda r: (not r[0].selected, -r[0].priority_score))

    return {
        "plan_id": str(plan.plan_id),
        "school_id": school_id,
        "budget_ceiling": plan.budget_ceiling,
        "currency": plan.currency,
        "granularity_used": plan.granularity_used,
        "mandatory_cost": plan.mandatory_cost,
        "optimized_cost": plan.optimized_cost,
        "total_spent": plan.total_spent,
        "over_budget_on_mandatory": plan.over_budget_on_mandatory,
        "total_priority_score_available": plan.total_priority_score_available,
        "total_priority_score_covered": plan.total_priority_score_covered,
        "coverage_pct": plan.coverage_pct,
        "triggered_by": plan.triggered_by,
        "created_at": plan.created_at.isoformat() if plan.created_at else None,
        "allocations": [
            {
                "problem_id": str(problem.problem_id),
                "title": problem.title,
                "category": problem.category,
                "cost": alloc.cost,
                "priority_score": alloc.priority_score,
                "selected": alloc.selected,
                "selection_reason": alloc.selection_reason,
                "score_per_currency_unit": alloc.score_per_currency_unit,
            }
            for alloc, problem in rows
        ],
    }


@router.get("/school/{school_id}/plans")
async def get_plan_history(school_id: str, db: AsyncSession = Depends(get_db)):
    await _require_school(db, school_id)
    result = await db.execute(
        select(BudgetPlan).where(BudgetPlan.school_id == school_id).order_by(BudgetPlan.created_at.desc())
    )
    plans = result.scalars().all()
    return {
        "school_id": school_id,
        "plans": [
            {
                "plan_id": str(p.plan_id),
                "budget_ceiling": p.budget_ceiling,
                "total_spent": p.total_spent,
                "coverage_pct": p.coverage_pct,
                "over_budget_on_mandatory": p.over_budget_on_mandatory,
                "triggered_by": p.triggered_by,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in plans
        ],
    }


@router.put("/cost/{problem_id}")
async def override_cost(problem_id: uuid.UUID, body: CostOverrideRequest, db: AsyncSession = Depends(get_db)):
    problem = await db.get(Problem, problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")

    estimate = await set_manual_cost(
        db, problem_id=problem_id, school_id=body.school_id,
        cost=body.cost, notes=body.notes, created_by=body.created_by,
    )
    return {
        "estimate_id": str(estimate.estimate_id),
        "problem_id": str(problem_id),
        "estimated_cost": estimate.estimated_cost,
        "source": estimate.source,
        "notes": estimate.notes,
    }


@router.get("/cost/{problem_id}")
async def get_cost(problem_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ProblemCostEstimate).where(
            ProblemCostEstimate.problem_id == problem_id,
            ProblemCostEstimate.is_latest == True,  # noqa: E712
        )
    )
    estimate = result.scalars().first()
    if not estimate:
        raise HTTPException(status_code=404, detail="No cost estimate yet for this problem. Run a budget plan first, or PUT a manual override.")
    return {
        "problem_id": str(problem_id),
        "estimated_cost": estimate.estimated_cost,
        "currency": estimate.currency,
        "source": estimate.source,
        "notes": estimate.notes,
        "computed_at": estimate.created_at.isoformat() if estimate.created_at else None,
    }