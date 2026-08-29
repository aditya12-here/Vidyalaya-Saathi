from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
from pydantic import BaseModel
import uuid

from app.database import get_db
from app.models.image import Problem

router = APIRouter(prefix="/problems", tags=["problems"])

class ManualProblemCreate(BaseModel):
    image_id: Optional[uuid.UUID] = None
    title: str
    category: str
    location: Optional[str] = None
    description: str
    human_priority: str
    human_notes: Optional[str] = None
    human_status: str = "Confirmed"
    image_coordinates: Optional[dict] = None

class ProblemReviewUpdate(BaseModel):
    human_status: str # "Confirmed", "Rejected", "Modified"
    human_priority: Optional[str] = None
    human_notes: Optional[str] = None
    title: Optional[str] = None
    condition: Optional[str] = None
    description: Optional[str] = None # For human edit overrides

@router.get("/school/{school_id}")
async def get_school_problems(school_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Problem).where(Problem.school_id == school_id))
    return result.scalars().all()

@router.post("/school/{school_id}/manual")
async def create_manual_problem(school_id: str, problem: ManualProblemCreate, db: AsyncSession = Depends(get_db)):
    """Allow an administrator/engineer to manually flag an issue"""
    new_problem = Problem(
        school_id=school_id,
        image_id=problem.image_id,
        source="ADMINISTRATOR", # Assume Admin for now
        title=problem.title,
        category=problem.category,
        location=problem.location,
        description=problem.description,
        human_priority=problem.human_priority,
        human_notes=problem.human_notes,
        human_status=problem.human_status,
        image_coordinates=problem.image_coordinates
    )
    db.add(new_problem)
    await db.commit()
    await db.refresh(new_problem)
    return new_problem

@router.put("/{problem_id}/review")
async def review_problem(problem_id: uuid.UUID, update_data: ProblemReviewUpdate, db: AsyncSession = Depends(get_db)):
    """Allow an administrator to review, confirm, reject, or edit an AI-generated problem"""
    problem = await db.get(Problem, problem_id)
    if not problem:
        raise HTTPException(status_code=404, detail="Problem not found")
        
    problem.human_status = update_data.human_status
    if update_data.human_priority:
        problem.human_priority = update_data.human_priority
    if update_data.human_notes:
        problem.human_notes = update_data.human_notes
    if update_data.title:
        problem.title = update_data.title
    if update_data.condition:
        problem.condition = update_data.condition
    if update_data.description and update_data.description != problem.description:
        # Preserve original AI observation
        if not problem.original_ai_observation and problem.source == 'AI':
             problem.original_ai_observation = problem.description
        problem.description = update_data.description
        problem.human_override = True
        
    db.add(problem)
    await db.commit()
    await db.refresh(problem)
    return problem
