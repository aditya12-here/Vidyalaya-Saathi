-- database/migrations/005_problem_image_evidence.sql

-- 1. Create junction table to allow multiple images per problem (deduplication & traceability)
CREATE TABLE IF NOT EXISTS problem_evidence (
    evidence_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    problem_id UUID NOT NULL REFERENCES problems(problem_id) ON DELETE CASCADE,
    image_id UUID NOT NULL REFERENCES school_images(image_id) ON DELETE CASCADE,
    
    -- We can store specific coordinates/bounding box in the join table
    -- so that one problem can have different highlights in different images
    image_coordinates JSONB, 
    
    is_primary BOOLEAN DEFAULT FALSE,
    added_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index for quick lookups
CREATE INDEX IF NOT EXISTS idx_problem_evidence_problem_id ON problem_evidence(problem_id);
CREATE INDEX IF NOT EXISTS idx_problem_evidence_image_id ON problem_evidence(image_id);

-- 2. Add 'status' to problem table for lifecycle support
-- e.g. 'Identified', 'Verified', 'Planned', 'In Progress', 'Resolved', 'Reassessed'
ALTER TABLE problems
ADD COLUMN IF NOT EXISTS lifecycle_status VARCHAR(50) DEFAULT 'Identified';

-- 3. We keep the direct `image_id` on the problem table for legacy/initial creation,
-- but the architectural shift relies on `problem_evidence` for multi-image deduction.
