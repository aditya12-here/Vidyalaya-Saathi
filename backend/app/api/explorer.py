# backend/app/api/explorer.py
#
# READ-ONLY router. Every endpoint here is a GET; nothing here writes to the
# database. Its purpose is purely to give a single place to see everything
# that exists in the backend for a school — school profile, every
# school_data record, every problem, and (if those features have been
# applied) the latest prioritization and budget results.
#
# Uses a generic SQLAlchemy-model-to-dict serializer instead of hand-written
# Pydantic schemas per table, so it automatically picks up any new column
# added to any of these models later without needing to be edited.

import uuid
from datetime import date, datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.models.image import School, Problem
from app.models.school_data import (
    StudentLearningData, StudentAttendance, StudentFeedback,
    TeacherData, TeacherFeedback, InfrastructureData,
)

router = APIRouter(prefix="/explorer", tags=["explorer"])

# These two feature model modules may or may not be present depending on
# which of the previous features have been applied to this checkout. Import
# defensively so the Explorer still works (with those sections omitted) even
# if, say, only the Prioritization Engine has been added so far and not yet
# the Budget Engine.
try:
    from app.models.prioritization import ProblemPriorityScore, PrioritizationRun
    _HAS_PRIORITIZATION = True
except ImportError:
    _HAS_PRIORITIZATION = False

try:
    from app.models.budget import ProblemCostEstimate, BudgetPlan, BudgetPlanAllocation
    _HAS_BUDGET = True
except ImportError:
    _HAS_BUDGET = False


def _serialize(obj) -> dict:
    """Generic SQLAlchemy model instance -> JSON-safe dict, via its own table columns."""
    if obj is None:
        return None
    result = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if isinstance(val, uuid.UUID):
            val = str(val)
        elif isinstance(val, (datetime, date)):
            val = val.isoformat()
        result[col.name] = val
    return result


async def _require_school(db: AsyncSession, school_id: str) -> School:
    school = await db.get(School, school_id)
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    return school


@router.get("/schools")
async def list_schools(db: AsyncSession = Depends(get_db)):
    """Every school with quick counts, for a top-level overview / school picker."""
    schools = (await db.execute(select(School))).scalars().all()

    out = []
    for school in schools:
        problem_count = len(
            (await db.execute(select(Problem).where(Problem.school_id == school.school_id))).scalars().all()
        )

        latest_run_at = None
        if _HAS_PRIORITIZATION:
            run = (
                await db.execute(
                    select(PrioritizationRun)
                    .where(PrioritizationRun.school_id == school.school_id)
                    .order_by(PrioritizationRun.created_at.desc())
                )
            ).scalars().first()
            latest_run_at = run.created_at.isoformat() if run and run.created_at else None

        latest_plan_at = None
        if _HAS_BUDGET:
            plan = (
                await db.execute(
                    select(BudgetPlan)
                    .where(BudgetPlan.school_id == school.school_id)
                    .order_by(BudgetPlan.created_at.desc())
                )
            ).scalars().first()
            latest_plan_at = plan.created_at.isoformat() if plan and plan.created_at else None

        out.append({
            "school_id": school.school_id,
            "name": school.name,
            "school_code": school.school_code,
            "state": school.state,
            "district": school.district,
            "total_enrollment": school.total_enrollment,
            "problem_count": problem_count,
            "prioritization_last_run_at": latest_run_at,
            "budget_plan_last_run_at": latest_plan_at,
        })
    return {"schools": out, "count": len(out)}


@router.get("/schools/{school_id}")
async def get_school_full_detail(school_id: str, db: AsyncSession = Depends(get_db)):
    """
    Everything that exists for one school: profile, all school_data records,
    all problems (with their latest priority score / cost estimate inlined
    if those features are present), and the latest prioritization run and
    budget plan (with allocations) if they exist.
    """
    school = await _require_school(db, school_id)

    async def _all(model, **filters):
        query = select(model).where(*[getattr(model, k) == v for k, v in filters.items()])
        rows = (await db.execute(query)).scalars().all()
        return [_serialize(r) for r in rows]

    school_data = {
        "learning": await _all(StudentLearningData, school_id=school_id),
        "attendance": await _all(StudentAttendance, school_id=school_id),
        "student_feedback": await _all(StudentFeedback, school_id=school_id),
        "teacher_data": await _all(TeacherData, school_id=school_id),
        "teacher_feedback": await _all(TeacherFeedback, school_id=school_id),
        "infrastructure": await _all(InfrastructureData, school_id=school_id),
    }

    problems = (await db.execute(select(Problem).where(Problem.school_id == school_id))).scalars().all()

    problems_out = []
    for problem in problems:
        problem_dict = _serialize(problem)

        if _HAS_PRIORITIZATION:
            score = (
                await db.execute(
                    select(ProblemPriorityScore).where(
                        ProblemPriorityScore.problem_id == problem.problem_id,
                        ProblemPriorityScore.is_latest == True,  # noqa: E712
                    )
                )
            ).scalars().first()
            problem_dict["latest_priority_score"] = _serialize(score)

        if _HAS_BUDGET:
            cost = (
                await db.execute(
                    select(ProblemCostEstimate).where(
                        ProblemCostEstimate.problem_id == problem.problem_id,
                        ProblemCostEstimate.is_latest == True,  # noqa: E712
                    )
                )
            ).scalars().first()
            problem_dict["latest_cost_estimate"] = _serialize(cost)

        problems_out.append(problem_dict)

    latest_run = None
    if _HAS_PRIORITIZATION:
        run = (
            await db.execute(
                select(PrioritizationRun)
                .where(PrioritizationRun.school_id == school_id)
                .order_by(PrioritizationRun.created_at.desc())
            )
        ).scalars().first()
        latest_run = _serialize(run)

    latest_plan = None
    if _HAS_BUDGET:
        plan = (
            await db.execute(
                select(BudgetPlan)
                .where(BudgetPlan.school_id == school_id)
                .order_by(BudgetPlan.created_at.desc())
            )
        ).scalars().first()
        if plan:
            allocations = (
                await db.execute(
                    select(BudgetPlanAllocation).where(BudgetPlanAllocation.plan_id == plan.plan_id)
                )
            ).scalars().all()
            latest_plan = _serialize(plan)
            latest_plan["allocations"] = [_serialize(a) for a in allocations]

    return {
        "school": _serialize(school),
        "school_data": school_data,
        "problems": problems_out,
        "latest_prioritization_run": latest_run,
        "latest_budget_plan": latest_plan,
        "features_detected": {
            "prioritization_engine": _HAS_PRIORITIZATION,
            "budget_engine": _HAS_BUDGET,
        },
    }