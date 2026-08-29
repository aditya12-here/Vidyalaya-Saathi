from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import date
import uuid

from app.database import get_db
from app.models.image import School
from app.models.school_data import (
    StudentLearningData, StudentAttendance, StudentFeedback,
    TeacherData, TeacherFeedback, InfrastructureData
)

router = APIRouter(prefix="/school-data", tags=["school-data"])

# --- Pydantic Schemas ---

class SchoolCreate(BaseModel):
    school_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=2)
    school_code: Optional[str] = None
    state: Optional[str] = None
    district: Optional[str] = None
    block: Optional[str] = None
    location_info: Optional[str] = None
    school_type: Optional[str] = None
    grades_served: Optional[str] = None
    total_enrollment: Optional[int] = Field(None, ge=0)
    num_classrooms: Optional[int] = Field(None, ge=0)
    num_teachers: Optional[int] = Field(None, ge=0)
    
    # We must treat empty string as None for uniqueness constraints
    def model_dump(self, *args, **kwargs):
        data = super().model_dump(*args, **kwargs)
        if data.get('school_code') == "":
            data['school_code'] = None
        return data

class StudentLearningCreate(BaseModel):
    grade: str
    assessment_type: str
    competency: str
    expected_level: Optional[str] = None
    observed_level: Optional[str] = None
    students_assessed: Optional[int] = Field(None, ge=0)
    students_at_level: Optional[int] = Field(None, ge=0)
    assessment_date: Optional[date] = None

class AttendanceCreate(BaseModel):
    grade: Optional[str] = None
    time_period: Optional[str] = None
    students_enrolled: Optional[int] = Field(None, ge=0)
    students_present: Optional[int] = Field(None, ge=0)
    attendance_percentage: Optional[float] = Field(None, ge=0, le=100)
    chronic_absenteeism_count: Optional[int] = Field(None, ge=0)

class TeacherDataCreate(BaseModel):
    teachers_required: Optional[int] = Field(None, ge=0)
    teachers_sanctioned: Optional[int] = Field(None, ge=0)
    teachers_available: Optional[int] = Field(None, ge=0)
    vacancies: Optional[int] = Field(None, ge=0)
    teachers_absent: Optional[int] = Field(None, ge=0)
    avg_students_per_teacher: Optional[float] = Field(None, ge=0)
    avg_teaching_hours: Optional[int] = Field(None, ge=0)
    avg_admin_hours: Optional[int] = Field(None, ge=0)

class InfrastructureCreate(BaseModel):
    category: str
    availability: Optional[str] = None
    quantity: Optional[int] = Field(None, ge=0)
    required_quantity: Optional[int] = Field(None, ge=0)
    condition: Optional[str] = None
    functional_status: Optional[str] = None
    last_inspection: Optional[date] = None
    notes: Optional[str] = None

# --- API Endpoints ---

@router.post("/schools")
async def create_school(school: SchoolCreate, db: AsyncSession = Depends(get_db)):
    new_school = School(**school.model_dump())
    db.add(new_school)
    try:
        await db.commit()
        await db.refresh(new_school)
        return new_school
    except IntegrityError as e:
        await db.rollback()
        # Look for UNIQUE constraint failure
        if "UNIQUE constraint failed" in str(e) and "school_code" in str(e):
            raise HTTPException(status_code=400, detail="A school with this UDISE / School Code already exists.")
        raise HTTPException(status_code=400, detail="Database integrity error.")

@router.post("/{school_id}/learning")
async def add_learning_data(school_id: str, data: StudentLearningCreate, db: AsyncSession = Depends(get_db)):
    # Validate school exists
    school = await db.get(School, school_id)
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
        
    learning = StudentLearningData(school_id=school_id, **data.model_dump())
    db.add(learning)
    await db.commit()
    await db.refresh(learning)
    return learning

@router.post("/{school_id}/attendance")
async def add_attendance_data(school_id: str, data: AttendanceCreate, db: AsyncSession = Depends(get_db)):
    school = await db.get(School, school_id)
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
        
    attendance = StudentAttendance(school_id=school_id, **data.model_dump())
    db.add(attendance)
    await db.commit()
    await db.refresh(attendance)
    return attendance

@router.post("/{school_id}/teachers")
async def update_teacher_data(school_id: str, data: TeacherDataCreate, db: AsyncSession = Depends(get_db)):
    school = await db.get(School, school_id)
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
        
    # Generally teacher data might be updated rather than strictly append-only,
    # but for simplicity in this phase we will insert a new snapshot.
    t_data = TeacherData(school_id=school_id, **data.model_dump())
    db.add(t_data)
    await db.commit()
    await db.refresh(t_data)
    return t_data

@router.post("/{school_id}/infrastructure")
async def add_infrastructure(school_id: str, data: InfrastructureCreate, db: AsyncSession = Depends(get_db)):
    school = await db.get(School, school_id)
    if not school:
        raise HTTPException(status_code=404, detail="School not found")
        
    infra = InfrastructureData(school_id=school_id, **data.model_dump())
    db.add(infra)
    await db.commit()
    await db.refresh(infra)
    return infra
