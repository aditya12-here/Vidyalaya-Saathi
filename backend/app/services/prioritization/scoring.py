# backend/app/services/prioritization/scoring.py
#
# The core multi-criteria scoring algorithm. Pure functions only — no DB
# access here (that's engine.py's job) — so this module is trivially unit
# testable. See docs/prioritization_algorithm.md for the full methodology
# write-up.
#
# total_score = 100 * ( Ws*S_severity + Wi*S_impact + Wr*S_reach
#                      + Wu*S_urgency + Wc*S_confidence + Wx*S_context )
# then clamped upward to >= 90 if a safety_override condition fires.

import math
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.models.image import Problem
from app.services.prioritization.context import SchoolContext
from app.services.prioritization.weights import ResolvedWeights

# ---------------------------------------------------------------------------
# Lookup tables (tunable constants)
# ---------------------------------------------------------------------------

SEVERITY_MAP = {"critical": 1.0, "high": 0.75, "medium": 0.5, "low": 0.25}
SEVERITY_DEFAULT = 0.35  # 'Unknown' / 'requires inspection' / unrecognized string

CONDITION_MAP = {"critical": 1.0, "poor": 0.8, "fair": 0.5, "good": 0.1}
CONDITION_DEFAULT = 0.4

IMPACT_LEVEL_MAP = {"high": 1.0, "medium": 0.6, "low": 0.3}
IMPACT_LEVEL_DEFAULT = 0.4

# Baseline fraction of the school population assumed affected by a problem in
# this category, used when we can't extract a concrete headcount from
# `scale_estimate`. Categories match the fixed list enforced in
# backend/app/api/images.py's `valid_categories`.
CATEGORY_REACH_BASELINE = {
    "Drinking Water": 1.0,
    "Toilets": 0.9,
    "Electricity": 0.8,
    "Boundary/School Premises": 0.7,
    "School Building": 0.7,
    "Road/Access to School": 0.6,
    "Playground": 0.5,
    "Surrounding Area": 0.3,
    "Classroom": 0.3,
    "Furniture": 0.2,
    "Other": 0.2,
}
CATEGORY_REACH_DEFAULT = 0.25

# Categories where a "Critical" condition implies physical danger, not just
# inconvenience — these can trip the safety override.
SAFETY_CRITICAL_CATEGORIES = {"Electricity", "Boundary/School Premises", "School Building", "Drinking Water"}

# S_context correlation rules: (categories this applies to, context predicate, contribution, note)
def _context_rules(problem_category: str, ctx: SchoolContext):
    rules = [
        (
            {"Toilets", "Drinking Water", "Boundary/School Premises", "Road/Access to School"},
            ctx.attendance_low_flag,
            0.5,
            "School attendance is below threshold; this category is known to correlate with attendance issues.",
        ),
        (
            {"Classroom", "Furniture", "School Building"},
            ctx.fln_gap_flag,
            0.5,
            "Significant FLN/learning-level gaps observed; learning-environment issues compound this.",
        ),
        (
            {"Classroom", "School Building", "Furniture"},
            ctx.teacher_shortage_flag,
            0.3,
            "Teacher shortage/overload increases the operational burden of this issue.",
        ),
        (
            {"Toilets", "Drinking Water", "Boundary/School Premises"},
            (ctx.chronic_absenteeism_ratio is not None and ctx.chronic_absenteeism_ratio > 0.10),
            0.2,
            "Elevated chronic absenteeism ratio observed for this school.",
        ),
    ]
    fired = []
    total = 0.0
    for categories, condition_met, contribution, note in rules:
        if problem_category in categories and condition_met:
            fired.append(note)
            total += contribution
    return min(total, 1.0), fired


@dataclass
class ScoreResult:
    problem_id: str
    total_score: float
    tier: str
    safety_override: bool
    severity_score: float
    impact_score: float
    reach_score: float
    urgency_score: float
    confidence_score: float
    context_score: float
    breakdown: Dict[str, Any] = field(default_factory=dict)


def _severity_subscore(problem: Problem) -> float:
    sev = SEVERITY_MAP.get((problem.severity_estimate or "").strip().lower(), SEVERITY_DEFAULT)
    cond = CONDITION_MAP.get((problem.condition or "").strip().lower(), CONDITION_DEFAULT)
    return round(0.7 * sev + 0.3 * cond, 4)


def _impact_subscore(problem: Problem) -> float:
    student_impact = problem.student_impact or {}
    teacher_impact = problem.teacher_impact or {}

    student_val = IMPACT_LEVEL_MAP.get(str(student_impact.get("level", "")).strip().lower(), IMPACT_LEVEL_DEFAULT)
    teacher_val = IMPACT_LEVEL_MAP.get(str(teacher_impact.get("level", "")).strip().lower(), IMPACT_LEVEL_DEFAULT)

    areas = set(student_impact.get("areas") or []) | set(teacher_impact.get("areas") or [])
    breadth_bonus = min(len(areas) / 4.0, 1.0) * 0.15

    base = 0.6 * student_val + 0.4 * teacher_val
    return round(min(base + breadth_bonus, 1.0), 4)


def _extract_headcount(scale_estimate: Optional[str]) -> Optional[int]:
    if not scale_estimate:
        return None
    match = re.search(r"\d+", scale_estimate)
    return int(match.group()) if match else None


def _reach_subscore(problem: Problem, ctx: SchoolContext) -> float:
    category_baseline = CATEGORY_REACH_BASELINE.get(problem.category, CATEGORY_REACH_DEFAULT)
    headcount = _extract_headcount(problem.scale_estimate)

    if headcount is not None and ctx.total_enrollment and ctx.total_enrollment > 0:
        ratio = min(headcount / ctx.total_enrollment, 1.0)
        return round(0.7 * ratio + 0.3 * category_baseline, 4)

    return round(category_baseline, 4)


def _urgency_subscore(problem: Problem, now: datetime) -> float:
    inspection_component = 1.0 if problem.requires_inspection else 0.3

    created_at = problem.created_at
    staleness_component = 0.0
    if created_at is not None:
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        days_open = max((now - created_at).total_seconds() / 86400.0, 0.0)
        # Saturating growth: ~0 at day 0, ~0.63 at 30 days, ~0.95 at 90 days.
        staleness_component = 1 - math.exp(-days_open / 30.0)

    # Resolved problems shouldn't accrue urgency pressure.
    if (problem.lifecycle_status or "").strip().lower() == "resolved":
        return 0.0

    return round(min(0.6 * inspection_component + 0.4 * staleness_component, 1.0), 4)


def _confidence_subscore(problem: Problem) -> float:
    if problem.source == "AI":
        base = problem.confidence if problem.confidence is not None else 0.5
        if (problem.human_status or "").strip() == "Confirmed":
            trust_factor = 1.0
        elif (problem.human_status or "").strip() == "Rejected":
            trust_factor = 0.0  # shouldn't reach scoring, but defensive
        else:
            trust_factor = 0.6  # Pending Review — unverified AI claim
        score = base * trust_factor
    else:
        # ADMINISTRATOR / ENGINEER entries are human-sourced; trust them highly
        score = 1.0 if (problem.human_status or "").strip() == "Confirmed" else 0.85

    if problem.human_override:
        score = min(score + 0.05, 1.0)

    return round(max(min(score, 1.0), 0.0), 4)


def _context_subscore(problem: Problem, ctx: SchoolContext) -> (float, List[str]):
    score, fired_notes = _context_rules(problem.category, ctx)
    if not fired_notes:
        # Neutral-low baseline instead of 0: we don't want to unfairly punish
        # a problem just because this school hasn't logged attendance/FLN/
        # teacher data yet — that's a data-collection gap, not evidence the
        # problem is unimportant.
        score = 0.2
    return round(score, 4), fired_notes


def _tier_for_score(total_score: float) -> str:
    if total_score >= 85:
        return "Critical"
    if total_score >= 65:
        return "High"
    if total_score >= 40:
        return "Medium"
    return "Low"


def _check_safety_override(problem: Problem) -> bool:
    if (problem.condition or "").strip().lower() == "critical" and problem.category in SAFETY_CRITICAL_CATEGORIES:
        return True

    student_impact = problem.student_impact or {}
    if str(student_impact.get("level", "")).strip().lower() == "high":
        areas = [str(a).lower() for a in (student_impact.get("areas") or [])]
        if any("safety" in a for a in areas):
            return True

    return False


def score_problem(
    problem: Problem,
    ctx: SchoolContext,
    weights: ResolvedWeights,
    now: Optional[datetime] = None,
) -> ScoreResult:
    now = now or datetime.now(timezone.utc)

    s_severity = _severity_subscore(problem)
    s_impact = _impact_subscore(problem)
    s_reach = _reach_subscore(problem, ctx)
    s_urgency = _urgency_subscore(problem, now)
    s_confidence = _confidence_subscore(problem)
    s_context, context_notes = _context_subscore(problem, ctx)

    weighted_sum = (
        weights.weight_severity * s_severity
        + weights.weight_impact * s_impact
        + weights.weight_reach * s_reach
        + weights.weight_urgency * s_urgency
        + weights.weight_confidence * s_confidence
        + weights.weight_context * s_context
    )
    raw_total = round(weighted_sum * 100, 2)

    safety_override = _check_safety_override(problem)
    total_score = max(raw_total, 90.0) if safety_override else raw_total
    total_score = round(min(total_score, 100.0), 2)

    tier = _tier_for_score(total_score)

    breakdown = {
        "weights_used": weights.as_dict(),
        "raw_weighted_total_before_override": raw_total,
        "safety_override_applied": safety_override,
        "sub_scores": {
            "severity": s_severity,
            "impact": s_impact,
            "reach": s_reach,
            "urgency": s_urgency,
            "confidence": s_confidence,
            "context": s_context,
        },
        "context_rules_fired": context_notes,
        "inputs_snapshot": {
            "category": problem.category,
            "condition": problem.condition,
            "severity_estimate": problem.severity_estimate,
            "confidence_raw": problem.confidence,
            "requires_inspection": problem.requires_inspection,
            "scale_estimate": problem.scale_estimate,
            "source": problem.source,
            "human_status": problem.human_status,
            "human_override": problem.human_override,
            "lifecycle_status": problem.lifecycle_status,
        },
    }

    return ScoreResult(
        problem_id=str(problem.problem_id),
        total_score=total_score,
        tier=tier,
        safety_override=safety_override,
        severity_score=s_severity,
        impact_score=s_impact,
        reach_score=s_reach,
        urgency_score=s_urgency,
        confidence_score=s_confidence,
        context_score=s_context,
        breakdown=breakdown,
    )
