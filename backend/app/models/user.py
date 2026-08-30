from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, text, Enum
from sqlalchemy.dialects.postgresql import UUID
from app.models.image import Base
import uuid
import enum

class Role(str, enum.Enum):
    DISTRICT_OFFICER = "DISTRICT_OFFICER"
    SCHOOL_MANAGEMENT = "SCHOOL_MANAGEMENT"
    SURVEYOR = "SURVEYOR"
    COMMUNITY = "COMMUNITY"

class User(Base):
    __tablename__ = 'users'

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    
    role = Column(Enum(Role), nullable=False, default=Role.COMMUNITY)
    
    # Global access (e.g. District Officer, Surveyor)
    is_global = Column(Boolean, default=False)
    
    # For School Management and Community, tie them to a specific school
    school_id = Column(String(255), ForeignKey('schools.school_id', ondelete='CASCADE'), nullable=True)
    
    # Used for community signups matching a valid school ID card (e.g. Student ID, Teacher ID)
    community_id_number = Column(String(100), nullable=True)

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"))
