from sqlalchemy import Column, String, Integer, Float, DateTime, ForeignKey, text, Date
from sqlalchemy.dialects.postgresql import UUID
import uuid
from app.models.image import Base

class StudentLearningData(Base):
    __tablename__ = 'student_learning_data'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id = Column(String(255), ForeignKey('schools.school_id', ondelete='CASCADE'), nullable=False)
    grade = Column(String(20), nullable=False)
    assessment_type = Column(String(50), nullable=False)
    competency = Column(String(100), nullable=False)
    expected_level = Column(String(50))
    observed_level = Column(String(50))
    students_assessed = Column(Integer)
    students_at_level = Column(Integer)
    assessment_date = Column(Date)
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

class StudentAttendance(Base):
    __tablename__ = 'student_attendance'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id = Column(String(255), ForeignKey('schools.school_id', ondelete='CASCADE'), nullable=False)
    grade = Column(String(20))
    time_period = Column(String(50))
    students_enrolled = Column(Integer)
    students_present = Column(Integer)
    attendance_percentage = Column(Float)
    chronic_absenteeism_count = Column(Integer)
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

class StudentFeedback(Base):
    __tablename__ = 'student_feedback'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id = Column(String(255), ForeignKey('schools.school_id', ondelete='CASCADE'), nullable=False)
    grade = Column(String(20))
    category = Column(String(100), nullable=False)
    feedback_score = Column(Integer)
    feedback_text = Column(String)
    responses_count = Column(Integer)
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

class TeacherData(Base):
    __tablename__ = 'teacher_data'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id = Column(String(255), ForeignKey('schools.school_id', ondelete='CASCADE'), nullable=False)
    teachers_required = Column(Integer)
    teachers_sanctioned = Column(Integer)
    teachers_available = Column(Integer)
    vacancies = Column(Integer)
    teachers_absent = Column(Integer)
    avg_students_per_teacher = Column(Float)
    avg_teaching_hours = Column(Integer)
    avg_admin_hours = Column(Integer)
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP"))

class TeacherFeedback(Base):
    __tablename__ = 'teacher_feedback'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id = Column(String(255), ForeignKey('schools.school_id', ondelete='CASCADE'), nullable=False)
    category = Column(String(100), nullable=False)
    topic = Column(String(100), nullable=False)
    feedback_text = Column(String)
    severity = Column(String(50))
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

class InfrastructureData(Base):
    __tablename__ = 'infrastructure_data'
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id = Column(String(255), ForeignKey('schools.school_id', ondelete='CASCADE'), nullable=False)
    category = Column(String(100), nullable=False)
    availability = Column(String(50))
    quantity = Column(Integer)
    required_quantity = Column(Integer)
    condition = Column(String(50))
    functional_status = Column(String(50))
    last_inspection = Column(Date)
    notes = Column(String)
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP"))
