# backend/app/models/budget.py
#
# New SQLAlchemy models for the Budget Optimization Engine. Additive only —
# does not modify any existing model file, including
# app/models/prioritization.py from the previous feature.
#


from sqlalchemy import Column, String, Float, Boolean, DateTime, ForeignKey, text, Text
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.models.image import Base


class ProblemCostEstimate(Base):
    """
    Versioned cost estimate for a problem. is_latest=True marks the current
    estimate used by the budget optimizer. A HEURISTIC estimate can later be
    superseded by an ADMIN_OVERRIDE (a real quote) without losing history.
    """
    __tablename__ = 'problem_cost_estimates'

    estimate_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    problem_id = Column(UUID(as_uuid=True), ForeignKey('problems.problem_id', ondelete='CASCADE'), nullable=False)
    school_id = Column(String(255), ForeignKey('schools.school_id', ondelete='CASCADE'), nullable=False)

    estimated_cost = Column(Float, nullable=False)
    currency = Column(String(10), nullable=False, default='INR')
    source = Column(String(30), nullable=False, default='HEURISTIC')  # 'HEURISTIC' | 'ADMIN_OVERRIDE'
    notes = Column(Text, nullable=True)
    is_latest = Column(Boolean, nullable=False, default=True)

    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))


class BudgetPlan(Base):
    """
    One row per execution of the budget optimizer for a school. Records the
    budget ceiling used, how much went to mandatory (safety-critical) items
    vs. the knapsack-optimized remainder, and overall coverage.
    """
    __tablename__ = 'budget_plans'

    plan_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id = Column(String(255), ForeignKey('schools.school_id', ondelete='CASCADE'), nullable=False)

    budget_ceiling = Column(Float, nullable=False)
    currency = Column(String(10), nullable=False, default='INR')
    granularity_used = Column(Float, nullable=False)

    mandatory_cost = Column(Float, nullable=False, default=0)
    optimized_cost = Column(Float, nullable=False, default=0)
    total_spent = Column(Float, nullable=False, default=0)
    over_budget_on_mandatory = Column(Boolean, nullable=False, default=False)

    total_priority_score_available = Column(Float, nullable=False, default=0)
    total_priority_score_covered = Column(Float, nullable=False, default=0)
    coverage_pct = Column(Float, nullable=False, default=0)

    triggered_by = Column(String(100), nullable=True)
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))


class BudgetPlanAllocation(Base):
    """
    Line item: for a given plan, whether a specific problem was funded, and
    why (mandatory safety item vs. knapsack-optimized selection vs. left out).
    """
    __tablename__ = 'budget_plan_allocations'

    allocation_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id = Column(UUID(as_uuid=True), ForeignKey('budget_plans.plan_id', ondelete='CASCADE'), nullable=False)
    problem_id = Column(UUID(as_uuid=True), ForeignKey('problems.problem_id', ondelete='CASCADE'), nullable=False)

    selected = Column(Boolean, nullable=False)
    selection_reason = Column(String(30), nullable=False)  # 'MANDATORY_SAFETY' | 'OPTIMIZED' | 'NOT_SELECTED'
    cost = Column(Float, nullable=False)
    priority_score = Column(Float, nullable=False)
    score_per_currency_unit = Column(Float, nullable=True)

    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))