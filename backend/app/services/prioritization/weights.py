# backend/app/services/prioritization/weights.py
#
# Loads and manages the tunable weights used by the scoring algorithm.
# Weights are persisted in the DB (prioritization_weight_configs) so they can
# be changed at runtime via the API without a redeploy. Resolution order for
# "what weights apply to school X":
#   1. An active (is_active=True) config row scoped to that school_id.
#   2. An active config row with school_id = NULL (the global default).
#   3. Hardcoded fallback defaults (DEFAULT_WEIGHTS below) if the DB has
#      no config rows at all yet (e.g. brand-new install).

from dataclasses import dataclass, asdict
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.prioritization import PrioritizationWeightConfig

WEIGHT_FIELDS = (
    "weight_severity",
    "weight_impact",
    "weight_reach",
    "weight_urgency",
    "weight_confidence",
    "weight_context",
)

DEFAULT_WEIGHTS = {
    "weight_severity": 0.30,
    "weight_impact": 0.25,
    "weight_reach": 0.15,
    "weight_urgency": 0.10,
    "weight_confidence": 0.10,
    "weight_context": 0.10,
}


@dataclass
class ResolvedWeights:
    weight_severity: float
    weight_impact: float
    weight_reach: float
    weight_urgency: float
    weight_confidence: float
    weight_context: float
    source: str  # 'school', 'global', or 'hardcoded_default'

    def as_dict(self) -> dict:
        return asdict(self)

    def normalized(self) -> "ResolvedWeights":
        """
        Defensive normalization: if an admin sets weights that don't sum to
        1.0, we rescale proportionally rather than silently producing scores
        outside the intended [0, 100] range.
        """
        total = sum(getattr(self, f) for f in WEIGHT_FIELDS)
        if total <= 0:
            return ResolvedWeights(**DEFAULT_WEIGHTS, source="hardcoded_default")
        if abs(total - 1.0) < 1e-6:
            return self
        scaled = {f: getattr(self, f) / total for f in WEIGHT_FIELDS}
        return ResolvedWeights(**scaled, source=self.source + "_normalized")


async def get_active_weights(db: AsyncSession, school_id: str) -> ResolvedWeights:
    """Resolve the weights that should be used for a given school."""
    # 1. School-specific active config
    result = await db.execute(
        select(PrioritizationWeightConfig).where(
            PrioritizationWeightConfig.school_id == school_id,
            PrioritizationWeightConfig.is_active == True,  # noqa: E712
        ).order_by(PrioritizationWeightConfig.created_at.desc())
    )
    row = result.scalars().first()
    if row:
        return ResolvedWeights(
            **{f: getattr(row, f) for f in WEIGHT_FIELDS}, source="school"
        ).normalized()

    # 2. Global default active config
    result = await db.execute(
        select(PrioritizationWeightConfig).where(
            PrioritizationWeightConfig.school_id.is_(None),
            PrioritizationWeightConfig.is_active == True,  # noqa: E712
        ).order_by(PrioritizationWeightConfig.created_at.desc())
    )
    row = result.scalars().first()
    if row:
        return ResolvedWeights(
            **{f: getattr(row, f) for f in WEIGHT_FIELDS}, source="global"
        ).normalized()

    # 3. Hardcoded fallback
    return ResolvedWeights(**DEFAULT_WEIGHTS, source="hardcoded_default")


async def set_weights(
    db: AsyncSession,
    weights: dict,
    school_id: Optional[str] = None,
    created_by: Optional[str] = None,
) -> PrioritizationWeightConfig:
    """
    Create a new active weight config (scoped globally if school_id is None,
    or to a specific school), and deactivate any previously active config in
    that same scope. Old configs are kept (is_active=False) for audit history
    instead of being deleted.
    """
    missing = [f for f in WEIGHT_FIELDS if f not in weights]
    if missing:
        raise ValueError(f"Missing weight fields: {missing}")

    # Deactivate existing active config(s) in this scope
    result = await db.execute(
        select(PrioritizationWeightConfig).where(
            PrioritizationWeightConfig.school_id == school_id,
            PrioritizationWeightConfig.is_active == True,  # noqa: E712
        )
    )
    for existing in result.scalars().all():
        existing.is_active = False
        db.add(existing)

    new_config = PrioritizationWeightConfig(
        school_id=school_id,
        is_active=True,
        created_by=created_by,
        **{f: float(weights[f]) for f in WEIGHT_FIELDS},
    )
    db.add(new_config)
    await db.commit()
    await db.refresh(new_config)
    return new_config
