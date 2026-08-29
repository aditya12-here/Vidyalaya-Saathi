-- database/migrations/001_initial_schema.sql

CREATE TABLE IF NOT EXISTS schools (
    school_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS school_images (
    image_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id UUID NOT NULL REFERENCES schools(school_id) ON DELETE CASCADE,
    category VARCHAR(50) NOT NULL,
    description TEXT,
    storage_reference VARCHAR(512) NOT NULL, -- e.g., s3://bucket/path/to/image.jpg or local path for now
    filename VARCHAR(255) NOT NULL,
    mime_type VARCHAR(50) NOT NULL,
    file_size BIGINT NOT NULL,
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Index for querying images by school quickly
CREATE INDEX IF NOT EXISTS idx_school_images_school_id ON school_images(school_id);
