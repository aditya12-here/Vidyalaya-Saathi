-- database/migrations/002_add_analysis_column.sql

ALTER TABLE school_images
ADD COLUMN IF NOT EXISTS analysis_result JSONB;
