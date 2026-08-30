from pydantic import BaseModel, Field
from typing import Optional

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
    id: Optional[str] = Field(default=None, alias="_id")

    class Config:
        populate_by_name = True
