-- database/migrations/007_prioritization_engine.sql

CREATE TABLE IF NOT EXISTS prioritization_weight_configs (
    config_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id VARCHAR(255) REFERENCES schools(school_id) ON DELETE CASCADE, -- NULL = global default
    weight_severity DOUBLE PRECISION NOT NULL DEFAULT 0.30,
    weight_impact DOUBLE PRECISION NOT NULL DEFAULT 0.25,
    weight_reach DOUBLE PRECISION NOT NULL DEFAULT 0.15,
    weight_urgency DOUBLE PRECISION NOT NULL DEFAULT 0.10,
    weight_confidence DOUBLE PRECISION NOT NULL DEFAULT 0.10,
    weight_context DOUBLE PRECISION NOT NULL DEFAULT 0.10,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_by VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_weight_configs_school_id ON prioritization_weight_configs(school_id);


CREATE TABLE IF NOT EXISTS prioritization_runs (
    run_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id VARCHAR(255) NOT NULL REFERENCES schools(school_id) ON DELETE CASCADE,
    triggered_by VARCHAR(100), -- e.g. 'ADMIN', 'SYSTEM'
    weights_snapshot JSONB NOT NULL,     -- the weight config used for this run
    context_snapshot JSONB,              -- aggregated school_data signals used
    num_problems_scored INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_prioritization_runs_school_id ON prioritization_runs(school_id);


CREATE TABLE IF NOT EXISTS problem_priority_scores (
    score_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    problem_id UUID NOT NULL REFERENCES problems(problem_id) ON DELETE CASCADE,
    run_id UUID NOT NULL REFERENCES prioritization_runs(run_id) ON DELETE CASCADE,
    school_id VARCHAR(255) NOT NULL REFERENCES schools(school_id) ON DELETE CASCADE, -- denormalized for fast filtering

    total_score DOUBLE PRECISION NOT NULL,
    tier VARCHAR(20) NOT NULL, -- 'Critical' | 'High' | 'Medium' | 'Low'
    safety_override BOOLEAN NOT NULL DEFAULT FALSE,

    severity_score DOUBLE PRECISION NOT NULL,
    impact_score DOUBLE PRECISION NOT NULL,
    reach_score DOUBLE PRECISION NOT NULL,
    urgency_score DOUBLE PRECISION NOT NULL,
    confidence_score DOUBLE PRECISION NOT NULL,
    context_score DOUBLE PRECISION NOT NULL,

    breakdown JSONB NOT NULL, -- full explainability payload (weights, rules fired, raw inputs)
    is_latest BOOLEAN NOT NULL DEFAULT TRUE,

    computed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_priority_scores_problem_id ON problem_priority_scores(problem_id);
CREATE INDEX IF NOT EXISTS idx_priority_scores_school_id ON problem_priority_scores(school_id);
CREATE INDEX IF NOT EXISTS idx_priority_scores_is_latest ON problem_priority_scores(is_latest);
CREATE INDEX IF NOT EXISTS idx_priority_scores_run_id ON problem_priority_scores(run_id);
