from sqlalchemy import Column, String, Integer, BigInteger, DateTime, ForeignKey, text, JSON, Boolean, Float
from sqlalchemy.orm import declarative_base
from sqlalchemy.dialects.postgresql import UUID
import uuid

Base = declarative_base()

class School(Base):
    __tablename__ = 'schools'

    school_id = Column(String(255), primary_key=True)
    name = Column(String(255), nullable=False)
    school_code = Column(String(100), unique=True, nullable=True)
    state = Column(String(100), nullable=True)
    district = Column(String(100), nullable=True)
    block = Column(String(100), nullable=True)
    location_info = Column(String, nullable=True)
    school_type = Column(String(50), nullable=True)
    grades_served = Column(String(100), nullable=True)
    total_enrollment = Column(Integer, nullable=True)
    num_classrooms = Column(Integer, nullable=True)
    num_teachers = Column(Integer, nullable=True)
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

class SchoolImage(Base):
    __tablename__ = 'school_images'

    image_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id = Column(String(255), ForeignKey('schools.school_id', ondelete='CASCADE'), nullable=False)
    module = Column(String(100), nullable=True)
    category = Column(String(50), nullable=False)
    description = Column(String, nullable=True)
    storage_reference = Column(String(512), nullable=False)
    filename = Column(String(255), nullable=False)
    mime_type = Column(String(50), nullable=False)
    file_size = Column(BigInteger, nullable=False)
    uploaded_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    analysis_result = Column(JSON, nullable=True)

class ProblemEvidence(Base):
    __tablename__ = 'problem_evidence'
    
    evidence_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    problem_id = Column(UUID(as_uuid=True), ForeignKey('problems.problem_id', ondelete='CASCADE'), nullable=False)
    image_id = Column(UUID(as_uuid=True), ForeignKey('school_images.image_id', ondelete='CASCADE'), nullable=False)
    image_coordinates = Column(JSON, nullable=True)
    is_primary = Column(Boolean, default=False)
    added_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))

class Problem(Base):
    __tablename__ = 'problems'

    problem_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    school_id = Column(String(255), ForeignKey('schools.school_id', ondelete='CASCADE'), nullable=False)
    image_id = Column(UUID(as_uuid=True), ForeignKey('school_images.image_id', ondelete='SET NULL'), nullable=True)
    
    source = Column(String(50), nullable=False) # 'AI', 'ADMINISTRATOR', 'ENGINEER'
    
    title = Column(String(255), nullable=False)
    category = Column(String(100), nullable=False)
    location = Column(String(255), nullable=True)
    description = Column(String, nullable=False)
    
    condition = Column(String(50), nullable=True)
    severity_estimate = Column(String(50), nullable=True)
    confidence = Column(Float, nullable=True)
    requires_inspection = Column(Boolean, default=False)
    scale_estimate = Column(String(255), nullable=True)
    
    student_impact = Column(JSON, nullable=True)
    teacher_impact = Column(JSON, nullable=True)
    evidence = Column(JSON, nullable=True)
    
    human_priority = Column(String(50), nullable=True)
    human_notes = Column(String, nullable=True)
    human_status = Column(String(50), default='Pending Review')
    human_override = Column(Boolean, default=False)
    lifecycle_status = Column(String(50), default='Identified')
    
    image_coordinates = Column(JSON, nullable=True)
    original_ai_observation = Column(String, nullable=True)
    
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
    updated_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"), onupdate=text("CURRENT_TIMESTAMP"))
