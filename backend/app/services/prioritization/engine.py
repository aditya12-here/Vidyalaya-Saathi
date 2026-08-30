# backend/app/services/prioritization/engine.py
#
# Orchestrates a full prioritization run for a school:
#   1. Resolve active weights (weights.py)
#   2. Build school context from attendance/FLN/teacher data (context.py)
#   3. Fetch eligible Problem rows for the school
#   4. Score each one (scoring.py)
#   5. Persist: flip old scores' is_latest -> False, insert new scores,
#      insert one PrioritizationRun audit row
#   6. Return the ranked list
#
# This is the only module in the feature that writes prioritization data to
# the DB — api/prioritization.py should call into this rather than touching
# models directly.

from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.image import Problem
from app.models.prioritization import PrioritizationRun, ProblemPriorityScore
from app.services.prioritization.weights import get_active_weights
from app.services.prioritization.context import get_school_context
from app.services.prioritization.scoring import score_problem, ScoreResult

# Problems in these human_status / lifecycle_status states are excluded from
# scoring entirely — a rejected finding shouldn't compete for budget, and a
# resolved one no longer needs prioritizing.
EXCLUDED_HUMAN_STATUSES = {"Rejected"}
EXCLUDED_LIFECYCLE_STATUSES = {"Resolved", "Closed"}


async def _get_eligible_problems(db: AsyncSession, school_id: str) -> List[Problem]:
    result = await db.execute(select(Problem).where(Problem.school_id == school_id))
    all_problems = result.scalars().all()
    return [
        p for p in all_problems
        if (p.human_status not in EXCLUDED_HUMAN_STATUSES)
        and ((p.lifecycle_status or "Identified") not in EXCLUDED_LIFECYCLE_STATUSES)
    ]


async def run_prioritization(
    db: AsyncSession,
    school_id: str,
    triggered_by: Optional[str] = "SYSTEM",
) -> dict:
    """
    Executes a full prioritization run. Returns a dict with the run summary
    and the ranked list of ScoreResult-shaped dicts, sorted highest-priority
    first. Raises ValueError if the school has no eligible problems.
    """
    now = datetime.now(timezone.utc)

    weights = await get_active_weights(db, school_id)
    context = await get_school_context(db, school_id)
    problems = await _get_eligible_problems(db, school_id)

    if not problems:
        raise ValueError(f"No eligible problems found for school_id={school_id!r} to prioritize.")

    # Create the run record first so we have a run_id to attach scores to.
    run = PrioritizationRun(
        school_id=school_id,
        triggered_by=triggered_by,
        weights_snapshot=weights.as_dict(),
        context_snapshot=context.as_dict(),
        num_problems_scored=len(problems),
    )
    db.add(run)
    await db.flush()  # get run.run_id without committing yet

    # Demote any previously-latest scores for these specific problems.
    problem_ids = [p.problem_id for p in problems]
    if problem_ids:
        result = await db.execute(
            select(ProblemPriorityScore).where(
                ProblemPriorityScore.problem_id.in_(problem_ids),
                ProblemPriorityScore.is_latest == True,  # noqa: E712
            )
        )
        for old_score in result.scalars().all():
            old_score.is_latest = False
            db.add(old_score)

    results: List[ScoreResult] = []
    for problem in problems:
        score_result = score_problem(problem, context, weights, now=now)
        results.append(score_result)

        db.add(ProblemPriorityScore(
            problem_id=problem.problem_id,
            run_id=run.run_id,
            school_id=school_id,
            total_score=score_result.total_score,
            tier=score_result.tier,
            safety_override=score_result.safety_override,
            severity_score=score_result.severity_score,
            impact_score=score_result.impact_score,
            reach_score=score_result.reach_score,
            urgency_score=score_result.urgency_score,
            confidence_score=score_result.confidence_score,
            context_score=score_result.context_score,
            breakdown=score_result.breakdown,
            is_latest=True,
        ))

    await db.commit()
    await db.refresh(run)

    ranked = sorted(results, key=lambda r: r.total_score, reverse=True)

    return {
        "run_id": str(run.run_id),
        "school_id": school_id,
        "triggered_by": triggered_by,
        "weights_used": weights.as_dict(),
        "context_used": context.as_dict(),
        "num_problems_scored": len(problems),
        "created_at": run.created_at.isoformat() if run.created_at else now.isoformat(),
        "ranked_problems": [
            {
                "problem_id": r.problem_id,
                "total_score": r.total_score,
                "tier": r.tier,
                "safety_override": r.safety_override,
                "sub_scores": {
                    "severity": r.severity_score,
                    "impact": r.impact_score,
                    "reach": r.reach_score,
                    "urgency": r.urgency_score,
                    "confidence": r.confidence_score,
                    "context": r.context_score,
                },
                "breakdown": r.breakdown,
            }
            for r in ranked
        ],
    }
