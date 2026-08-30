# backend/app/api/prioritization.py
#
# Endpoints:
#   POST /api/v1/prioritization/school/{school_id}/run
#       -> executes the engine, returns run summary + ranked list
#   GET  /api/v1/prioritization/school/{school_id}
#       -> returns the current (latest) ranked list, joined with problem info
#          optional query param: tier=Critical|High|Medium|Low to filter
#   GET  /api/v1/prioritization/school/{school_id}/runs
#       -> run history (audit trail) for a school
#   GET  /api/v1/prioritization/weights?school_id=optional
#       -> the currently active weights that WOULD be used for this school
#   PUT  /api/v1/prioritization/weights
#       -> set new active weights (globally, or scoped to a school)

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Optional
from pydantic import BaseModel, Field

from app.database import get_db
from app.models.image import School, Problem
from app.models.prioritization import ProblemPriorityScore, PrioritizationRun
from app.services.prioritization.engine import run_prioritization
from app.services.prioritization.weights import get_active_weights, set_weights, WEIGHT_FIELDS

router = APIRouter(prefix="/prioritization", tags=["prioritization"])


class RunRequest(BaseModel):
    triggered_by: Optional[str] = "ADMIN"


class WeightsUpdate(BaseModel):
    school_id: Optional[str] = None  # None = set the global default
    created_by: Optional[str] = None
    weight_severity: float = Field(..., ge=0)
    weight_impact: float = Field(..., ge=0)
    weight_reach: float = Field(..., ge=0)
    weight_urgency: float = Field(..., ge=0)
    weight_confidence: float = Field(..., ge=0)
    weight_context: float = Field(..., ge=0)


async def _require_school(db: AsyncSession, school_id: str) -> School:
    school = await db.get(School, school_id)
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
    return school


@router.post("/school/{school_id}/run")
async def trigger_prioritization_run(
    school_id: str,
    body: RunRequest = RunRequest(),
    db: AsyncSession = Depends(get_db),
):
    """Score every eligible problem for a school and persist the results."""
    await _require_school(db, school_id)
    try:
        result = await run_prioritization(db, school_id, triggered_by=body.triggered_by)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return result


@router.get("/school/{school_id}")
async def get_ranked_problems(
    school_id: str,
    tier: Optional[str] = Query(None, description="Filter by tier: Critical, High, Medium, Low"),
    db: AsyncSession = Depends(get_db),
):
    """Current ranked list for a school, using the most recently computed score per problem."""
    await _require_school(db, school_id)

    query = (
        select(ProblemPriorityScore, Problem)
        .join(Problem, Problem.problem_id == ProblemPriorityScore.problem_id)
        .where(
            ProblemPriorityScore.school_id == school_id,
            ProblemPriorityScore.is_latest == True,  # noqa: E712
        )
        .order_by(ProblemPriorityScore.total_score.desc())
    )
    if tier:
        query = query.where(ProblemPriorityScore.tier == tier)

    result = await db.execute(query)
    rows = result.all()

    if not rows:
        return {
            "school_id": school_id,
            "message": "No priority scores yet. POST /prioritization/school/{school_id}/run first.",
            "ranked_problems": [],
        }

    return {
        "school_id": school_id,
        "count": len(rows),
        "ranked_problems": [
            {
                "problem_id": str(problem.problem_id),
                "title": problem.title,
                "category": problem.category,
                "location": problem.location,
                "source": problem.source,
                "human_status": problem.human_status,
                "total_score": score.total_score,
                "tier": score.tier,
                "safety_override": score.safety_override,
                "sub_scores": {
                    "severity": score.severity_score,
                    "impact": score.impact_score,
                    "reach": score.reach_score,
                    "urgency": score.urgency_score,
                    "confidence": score.confidence_score,
                    "context": score.context_score,
                },
                "breakdown": score.breakdown,
                "computed_at": score.computed_at.isoformat() if score.computed_at else None,
            }
            for score, problem in rows
        ],
    }


@router.get("/school/{school_id}/runs")
async def get_run_history(school_id: str, db: AsyncSession = Depends(get_db)):
    """Audit trail of every prioritization run executed for this school."""
    await _require_school(db, school_id)

    result = await db.execute(
        select(PrioritizationRun)
        .where(PrioritizationRun.school_id == school_id)
        .order_by(PrioritizationRun.created_at.desc())
    )
    runs = result.scalars().all()
    return {
        "school_id": school_id,
        "runs": [
            {
                "run_id": str(r.run_id),
                "triggered_by": r.triggered_by,
                "weights_snapshot": r.weights_snapshot,
                "context_snapshot": r.context_snapshot,
                "num_problems_scored": r.num_problems_scored,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in runs
        ],
    }


@router.get("/weights")
async def get_weights(
    school_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """The weights that would currently be applied for this school (or the global default)."""
    if school_id:
        await _require_school(db, school_id)
        resolved = await get_active_weights(db, school_id)
    else:
        # Resolution for "no school" = force fallthrough to global/default by
        # using a sentinel that can't match any real school_id.
        resolved = await get_active_weights(db, "__GLOBAL_ONLY__")
    return resolved.as_dict()


@router.put("/weights")
async def update_weights(body: WeightsUpdate, db: AsyncSession = Depends(get_db)):
    """
    Set new active scoring weights. If school_id is provided, scopes the
    change to that school only; otherwise updates the global default used by
    every school without its own override.
    """
    if body.school_id:
        await _require_school(db, body.school_id)

    weights_dict = {f: getattr(body, f) for f in WEIGHT_FIELDS}
    total = sum(weights_dict.values())
    if total <= 0:
        raise HTTPException(status_code=400, detail="Weights must sum to a positive value.")

    config = await set_weights(
        db, weights=weights_dict, school_id=body.school_id, created_by=body.created_by
    )
    return {
        "config_id": str(config.config_id),
        "school_id": config.school_id,
        "is_active": config.is_active,
        "weights": {f: getattr(config, f) for f in WEIGHT_FIELDS},
        "note": "Weights normalized to sum to 1.0 automatically when used for scoring." if abs(total - 1.0) > 1e-6 else None,
    }
