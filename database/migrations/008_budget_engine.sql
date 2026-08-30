-- database/migrations/008_budget_engine.sql

CREATE TABLE IF NOT EXISTS problem_cost_estimates (
    estimate_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    problem_id UUID NOT NULL REFERENCES problems(problem_id) ON DELETE CASCADE,
    school_id VARCHAR(255) NOT NULL REFERENCES schools(school_id) ON DELETE CASCADE,

    estimated_cost DOUBLE PRECISION NOT NULL,
    currency VARCHAR(10) NOT NULL DEFAULT 'INR',
    source VARCHAR(30) NOT NULL DEFAULT 'HEURISTIC', -- 'HEURISTIC' | 'ADMIN_OVERRIDE'
    notes TEXT,
    is_latest BOOLEAN NOT NULL DEFAULT TRUE,

    created_by VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_cost_estimates_problem_id ON problem_cost_estimates(problem_id);
CREATE INDEX IF NOT EXISTS idx_cost_estimates_school_id ON problem_cost_estimates(school_id);
CREATE INDEX IF NOT EXISTS idx_cost_estimates_is_latest ON problem_cost_estimates(is_latest);

-- 2. One row per budget optimization run (audit trail, like prioritization_runs).
CREATE TABLE IF NOT EXISTS budget_plans (
    plan_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id VARCHAR(255) NOT NULL REFERENCES schools(school_id) ON DELETE CASCADE,

    budget_ceiling DOUBLE PRECISION NOT NULL,
    currency VARCHAR(10) NOT NULL DEFAULT 'INR',
    granularity_used DOUBLE PRECISION NOT NULL,

    mandatory_cost DOUBLE PRECISION NOT NULL DEFAULT 0,
    optimized_cost DOUBLE PRECISION NOT NULL DEFAULT 0,
    total_spent DOUBLE PRECISION NOT NULL DEFAULT 0,
    over_budget_on_mandatory BOOLEAN NOT NULL DEFAULT FALSE,

    total_priority_score_available DOUBLE PRECISION NOT NULL DEFAULT 0,
    total_priority_score_covered DOUBLE PRECISION NOT NULL DEFAULT 0,
    coverage_pct DOUBLE PRECISION NOT NULL DEFAULT 0,

    triggered_by VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_budget_plans_school_id ON budget_plans(school_id);

-- 3. Line items: which problems were selected (and how) or left out, per plan.
CREATE TABLE IF NOT EXISTS budget_plan_allocations (
    allocation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id UUID NOT NULL REFERENCES budget_plans(plan_id) ON DELETE CASCADE,
    problem_id UUID NOT NULL REFERENCES problems(problem_id) ON DELETE CASCADE,

    selected BOOLEAN NOT NULL,
    selection_reason VARCHAR(30) NOT NULL, -- 'MANDATORY_SAFETY' | 'OPTIMIZED' | 'NOT_SELECTED'
    cost DOUBLE PRECISION NOT NULL,
    priority_score DOUBLE PRECISION NOT NULL,
    score_per_currency_unit DOUBLE PRECISION,

    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_budget_allocations_plan_id ON budget_plan_allocations(plan_id);
CREATE INDEX IF NOT EXISTS idx_budget_allocations_problem_id ON budget_plan_allocations(problem_id);