-- database/migrations/004_problem_coordinates_history.sql

ALTER TABLE problems
ADD COLUMN IF NOT EXISTS image_coordinates JSONB, -- For manual click flagging {x, y, width, height}
ADD COLUMN IF NOT EXISTS original_ai_observation TEXT, -- To preserve original AI text if edited by human
ADD COLUMN IF NOT EXISTS human_override BOOLEAN DEFAULT FALSE;
