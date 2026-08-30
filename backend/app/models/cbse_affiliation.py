from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy import Column, String, Integer, Float, Boolean
from app.models.image import Base

class CBSEAffiliationDBModel(Base):
    __tablename__ = "cbse_affiliation"
    
    id = Column(Integer, primary_key=True, index=True)
    schoolName = Column(String, index=True)
    stateNoc = Column(Boolean, default=False)
    fireSafetyCert = Column(Boolean, default=False)
    healthCert = Column(Boolean, default=False)
    buildingSafetyCert = Column(Boolean, default=False)
    totalStudent = Column(Integer)
    totalTeacher = Column(Integer)
    hasLibrary = Column(Boolean, default=False)
    hasScienceLab = Column(Boolean, default=False)
    hasMathLab = Column(Boolean, default=False)
    landArea = Column(Float)
    hasSeperateWashroom = Column(Boolean, default=False)
    status = Column(String)

class CBSEAffiliationCreate(BaseModel):
    schoolName: str = Field(..., description="Name of the school")
    stateNoc: bool = Field(default=False, description="State NOC certificate status")
    fireSafetyCert: bool = Field(default=False, description="Fire safety certificate status")
    healthCert: bool = Field(default=False, description="Health certificate status")
    buildingSafetyCert: bool = Field(default=False, description="Building safety certificate status")
    totalStudent: int = Field(..., description="Total number of students")
    totalTeacher: int = Field(..., description="Total number of teachers")
    hasLibrary: bool = Field(default=False, description="Whether the school has a library")
    hasScienceLab: bool = Field(default=False, description="Whether the school has a science lab")
    hasMathLab: bool = Field(default=False, description="Whether the school has a math lab")
    landArea: float = Field(..., description="Land area in square meters")
    hasSeperateWashroom: bool = Field(default=False, description="Whether the school has separate washrooms")

class CBSEAffiliationDB(CBSEAffiliationCreate):
    id: Optional[int] = Field(default=None)

    class Config:
        populate_by_name = True
        orm_mode = True
