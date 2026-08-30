import math
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.cbse_affiliation import CBSEAffiliationCreate, CBSEAffiliationDBModel
from app.database import get_db

router = APIRouter()

@router.post("/check", status_code=status.HTTP_200_OK)
async def check_cbse_affiliation(data: CBSEAffiliationCreate, db: AsyncSession = Depends(get_db)):
    try:
        # Mandatory conditions that must be present in a school
        mandatory_conditions = []
        if not data.fireSafetyCert:
            mandatory_conditions.append("fire safety cerificate is mendatory")
        if not data.stateNoc:
            mandatory_conditions.append("state noc is mendatory")
        if not data.healthCert:
            mandatory_conditions.append("health cerificate is mendatory")
        if not data.buildingSafetyCert:
            mandatory_conditions.append("building safety cerificate is mendatory")
        if not data.hasSeperateWashroom:
            mandatory_conditions.append("separate washroom is mendatory")
        
        # Recommendations for an ideal CBSE affiliated school
        recommendations = []
        
        # Student to teacher ratio
        required_teachers = math.ceil(data.totalStudent / 30)
        
        if data.totalTeacher < required_teachers:
            extra_needed = required_teachers - data.totalTeacher
            recommendations.append(f"need to hire atleast {extra_needed} extra teacher(s)")

        if data.landArea < 6000:
            recommendations.append(f"need atleast {6000 - data.landArea}sqm more land")

        if not data.hasLibrary:
            recommendations.append("library is required")
        if not data.hasMathLab:
            recommendations.append("math lab is required")
        if not data.hasScienceLab:
            recommendations.append("science lab is required")

        school_status = "NOT READY" if len(mandatory_conditions) > 0 else "READY"

        db_item = CBSEAffiliationDBModel(
            schoolName=data.schoolName,
            stateNoc=data.stateNoc,
            fireSafetyCert=data.fireSafetyCert,
            healthCert=data.healthCert,
            buildingSafetyCert=data.buildingSafetyCert,
            totalStudent=data.totalStudent,
            totalTeacher=data.totalTeacher,
            hasLibrary=data.hasLibrary,
            hasScienceLab=data.hasScienceLab,
            hasMathLab=data.hasMathLab,
            landArea=data.landArea,
            hasSeperateWashroom=data.hasSeperateWashroom,
            status=school_status
        )
        db.add(db_item)
        await db.commit()

        return {
            "success": True,
            "schoolName": data.schoolName,
            "status": school_status,
            "mendatoryCondition": mandatory_conditions,
            "recomendation": recommendations
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"success": False, "message": str(e)}
        )
