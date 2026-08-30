# backend/app/models/prioritization.py
#
# New SQLAlchemy models for the Prioritization Engine.
# Additive only — does not modify app/models/image.py or app/models/school_data.py.
#
# IMPORTANT: this file imports the SAME shared `Base` used by the rest of the app
# (from app.models.image import Base). Do not create a new declarative_base() here,
# or these tables will live in a disconnected metadata registry and main.py's
# `Base.metadata.create_all(...)` call won't create them.

from sqlalchemy import (
    Column, String, Float, Integer, Boolean, DateTime, ForeignKey, text, JSON
)
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.models.image import Base  # reuse the shared declarative base


class PrioritizationWeightConfig(Base):
    """
    Admin-tunable weights for the scoring algorithm.

    school_id = None (NULL) means this is the GLOBAL DEFAULT config, used for
    any school that doesn't have its own active config. A school can have at
    most one active (is_active=True) config at a time; enforced in the
    service layer (app/services/prioritization/weights.py), not via a DB
    constraint, to remain SQLite-compatible for local dev.
    """
    __tablename__ = 'prioritization_weight_configs'

    config_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id = Column(String(255), ForeignKey('schools.school_id', ondelete='CASCADE'), nullable=True)

    weight_severity = Column(Float, nullable=False, default=0.30)
    weight_impact = Column(Float, nullable=False, default=0.25)
    weight_reach = Column(Float, nullable=False, default=0.15)
    weight_urgency = Column(Float, nullable=False, default=0.10)
    weight_confidence = Column(Float, nullable=False, default=0.10)
    weight_context = Column(Float, nullable=False, default=0.10)

    is_active = Column(Boolean, nullable=False, default=True)
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))


class PrioritizationRun(Base):
    """
    Audit log: one row per execution of the engine for a given school.
    Stores exactly which weights and which aggregated school-data signals
    (context) were used, so every ranking is reproducible and explainable.
    """
    __tablename__ = 'prioritization_runs'

    run_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id = Column(String(255), ForeignKey('schools.school_id', ondelete='CASCADE'), nullable=False)

    triggered_by = Column(String(100), nullable=True)  # e.g. 'ADMIN', 'SYSTEM'
    weights_snapshot = Column(JSON, nullable=False)
    context_snapshot = Column(JSON, nullable=True)
    num_problems_scored = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))


class ProblemPriorityScore(Base):
    """
    One row per (problem, run). `is_latest=True` marks the current active
    score for a problem — the ranked-list endpoint filters on this. Older
    rows are kept (is_latest flips to False) rather than deleted, so score
    history over time is preserved.
    """
    __tablename__ = 'problem_priority_scores'

    score_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    problem_id = Column(UUID(as_uuid=True), ForeignKey('problems.problem_id', ondelete='CASCADE'), nullable=False)
    run_id = Column(UUID(as_uuid=True), ForeignKey('prioritization_runs.run_id', ondelete='CASCADE'), nullable=False)
    school_id = Column(String(255), ForeignKey('schools.school_id', ondelete='CASCADE'), nullable=False)

    total_score = Column(Float, nullable=False)
    tier = Column(String(20), nullable=False)  # 'Critical' | 'High' | 'Medium' | 'Low'
    safety_override = Column(Boolean, nullable=False, default=False)

    severity_score = Column(Float, nullable=False)
    impact_score = Column(Float, nullable=False)
    reach_score = Column(Float, nullable=False)
    urgency_score = Column(Float, nullable=False)
    confidence_score = Column(Float, nullable=False)
    context_score = Column(Float, nullable=False)

    breakdown = Column(JSON, nullable=False)
    is_latest = Column(Boolean, nullable=False, default=True)

    computed_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
