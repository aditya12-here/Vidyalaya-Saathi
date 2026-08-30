from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import uuid

from app.database import get_db
from app.models.image import SchoolImage, Problem, ProblemEvidence
from app.services.storage import save_upload_file_mock_s3, STORAGE_DIR
from app.services.ai.provider import vision_ai

router = APIRouter(prefix="/images", tags=["images"])

@router.post("/upload")
async def upload_image(
    background_tasks: BackgroundTasks,
    school_id: str = Form(...),
    module: str = Form(...),
   category: Optional[str] = Form("Other"),
    description: Optional[str] = Form(None),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload an image for a specific school and category.
    Initiates asynchronous vision AI analysis and saves problems into DB.
    """
    valid_categories = [
        "Classroom", "School Building", "Toilets", "Drinking Water", 
        "Electricity", "Furniture", "Playground", "Boundary/School Premises", 
        "Road/Access to School", "Surrounding Area", "Other"
    ]
    if not category or category not in valid_categories:
        category = "Other"
    if category not in valid_categories:
        raise HTTPException(status_code=400, detail=f"Invalid category. Must be one of {valid_categories}")

    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    
    storage_ref = await save_upload_file_mock_s3(file, file_size)
    filename = storage_ref.split("/")[-1]
    physical_file_path = str(STORAGE_DIR / filename)

    new_image = SchoolImage(
        school_id=school_id,
        module=module,
        category=category,
        description=description,
        storage_reference=storage_ref,
        filename=file.filename,
        mime_type=file.content_type,
        file_size=file_size
    )
    
    db.add(new_image)
    await db.commit()
    await db.refresh(new_image)

    # Note: In production this should be truly async via Celery/BackgroundTasks with its own DB Session.
    # We run it synchronously here so the frontend immediately receives the parsed data for review.
    try:
        # analysis_result = await vision_ai.analyze_image(physical_file_path, category, description)
        analysis_result = await vision_ai.analyze_image(physical_file_path, description=description)
        
        if analysis_result and hasattr(analysis_result, 'image_category'):
            new_image.category = analysis_result.image_category
            
        # Store the JSON dictionary on the model so the frontend receives it
        new_image.analysis_result = analysis_result.model_dump()
        db.add(new_image)
        await db.commit()
        # new_image.analysis_result = analysis_result.model_dump()
        # db.add(new_image)
        
        # Save individual problems discovered by AI (only if quality is sufficient)
        if analysis_result.image_quality.analysis_recommended:
            for prob in analysis_result.problems:
                new_problem = Problem(
                    school_id=school_id,
        module=module,
                    image_id=new_image.image_id, # Legacy direct tie, can be phased out for problem_evidence mapping
                    source="AI",
                    title=prob.problem,
                    category=prob.category,
                    location=prob.location,
                    description=prob.observation,
                    condition=prob.condition,
                    severity_estimate=prob.severity_estimate,
                    confidence=prob.confidence,
                    requires_inspection=prob.requires_inspection,
                    scale_estimate=prob.scale_estimate,
                    student_impact=prob.student_impact.model_dump(),
                    teacher_impact=prob.teacher_impact.model_dump(),
                    evidence=prob.evidence
                )
                db.add(new_problem)
                await db.flush() # get problem_id
                
                # Establish the many-to-many link to properly support deduplication mapping
                evidence_link = ProblemEvidence(
                    problem_id=new_problem.problem_id,
                    image_id=new_image.image_id,
                    is_primary=True
                )
                db.add(evidence_link)
                
        await db.commit()
    except Exception as e:
         print(f"Analysis failed: {e}")
         # Image uploaded, but AI failed
         
    return {
        "message": "Image uploaded and processed",
        "image_id": new_image.image_id,
        "analysis": new_image.analysis_result
    }
