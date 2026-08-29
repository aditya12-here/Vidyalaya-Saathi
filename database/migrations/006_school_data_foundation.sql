-- database/migrations/006_school_data_foundation.sql

-- 1. Expand School Table
ALTER TABLE schools
ADD COLUMN IF NOT EXISTS school_code VARCHAR(100) UNIQUE,
ADD COLUMN IF NOT EXISTS state VARCHAR(100),
ADD COLUMN IF NOT EXISTS district VARCHAR(100),
ADD COLUMN IF NOT EXISTS block VARCHAR(100),
ADD COLUMN IF NOT EXISTS location_info TEXT,
ADD COLUMN IF NOT EXISTS school_type VARCHAR(50), -- e.g., Primary, Upper Primary, Secondary
ADD COLUMN IF NOT EXISTS grades_served VARCHAR(100),
ADD COLUMN IF NOT EXISTS total_enrollment INTEGER,
ADD COLUMN IF NOT EXISTS num_classrooms INTEGER,
ADD COLUMN IF NOT EXISTS num_teachers INTEGER;

-- 2. Student Learning / FLN Data
CREATE TABLE IF NOT EXISTS student_learning_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id UUID NOT NULL REFERENCES schools(school_id) ON DELETE CASCADE,
    grade VARCHAR(20) NOT NULL,
    assessment_type VARCHAR(50) NOT NULL, -- e.g., 'READING', 'WRITING', 'NUMERACY'
    competency VARCHAR(100) NOT NULL, -- e.g., 'Word reading', 'Addition'
    expected_level VARCHAR(50),
    observed_level VARCHAR(50),
    students_assessed INTEGER,
    students_at_level INTEGER,
    assessment_date DATE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_student_learning_school_id ON student_learning_data(school_id);

-- 3. Student Attendance
CREATE TABLE IF NOT EXISTS student_attendance (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id UUID NOT NULL REFERENCES schools(school_id) ON DELETE CASCADE,
    grade VARCHAR(20),
    time_period VARCHAR(50), -- e.g., 'August 2026', 'Term 1'
    students_enrolled INTEGER,
    students_present INTEGER,
    attendance_percentage DOUBLE PRECISION,
    chronic_absenteeism_count INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_student_attendance_school_id ON student_attendance(school_id);

-- 4. Student Feedback
CREATE TABLE IF NOT EXISTS student_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id UUID NOT NULL REFERENCES schools(school_id) ON DELETE CASCADE,
    grade VARCHAR(20),
    category VARCHAR(100) NOT NULL, -- e.g., 'Safety', 'Hygiene'
    feedback_score INTEGER, -- Optional scale 1-5
    feedback_text TEXT,
    responses_count INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. Teacher Availability & Workload
CREATE TABLE IF NOT EXISTS teacher_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id UUID NOT NULL REFERENCES schools(school_id) ON DELETE CASCADE,
    teachers_required INTEGER,
    teachers_sanctioned INTEGER,
    teachers_available INTEGER,
    vacancies INTEGER,
    teachers_absent INTEGER,
    avg_students_per_teacher DOUBLE PRECISION,
    avg_teaching_hours INTEGER,
    avg_admin_hours INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 6. Teacher Support Needs & Feedback
CREATE TABLE IF NOT EXISTS teacher_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id UUID NOT NULL REFERENCES schools(school_id) ON DELETE CASCADE,
    category VARCHAR(100) NOT NULL, -- e.g., 'Support Need', 'General Feedback'
    topic VARCHAR(100) NOT NULL, -- e.g., 'FLN pedagogy', 'Teacher shortage'
    feedback_text TEXT,
    severity VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 7. Infrastructure Data
CREATE TABLE IF NOT EXISTS infrastructure_data (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    school_id UUID NOT NULL REFERENCES schools(school_id) ON DELETE CASCADE,
    category VARCHAR(100) NOT NULL, -- e.g., 'Classrooms', 'Toilets'
    availability VARCHAR(50), -- 'Available', 'Unavailable'
    quantity INTEGER,
    required_quantity INTEGER,
    condition VARCHAR(50), -- 'Good', 'Fair', 'Poor', 'Critical'
    functional_status VARCHAR(50),
    last_inspection DATE,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_infrastructure_school_id ON infrastructure_data(school_id);
