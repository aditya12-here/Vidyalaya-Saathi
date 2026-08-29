-- database/migrations/003_problems_schema.sql

CREATE TABLE IF NOT EXISTS problems (
    problem_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id UUID NOT NULL REFERENCES schools(school_id) ON DELETE CASCADE,
    image_id UUID REFERENCES school_images(image_id) ON DELETE SET NULL,
    source VARCHAR(50) NOT NULL, -- e.g., 'AI', 'ADMINISTRATOR', 'ENGINEER'
    
    title VARCHAR(255) NOT NULL,
    category VARCHAR(100) NOT NULL,
    location VARCHAR(255),
    description TEXT NOT NULL,
    
    condition VARCHAR(50),
    severity_estimate VARCHAR(50),
    confidence DOUBLE PRECISION,
    requires_inspection BOOLEAN DEFAULT FALSE,
    scale_estimate VARCHAR(255),
    
    student_impact JSONB,
    teacher_impact JSONB,
    evidence JSONB,
    
    human_priority VARCHAR(50),
    human_notes TEXT,
    human_status VARCHAR(50) DEFAULT 'Pending Review', -- 'Pending Review', 'Confirmed', 'Rejected'
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_problems_school_id ON problems(school_id);
CREATE INDEX IF NOT EXISTS idx_problems_source ON problems(source);
