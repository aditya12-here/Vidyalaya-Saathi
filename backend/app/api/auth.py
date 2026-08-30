from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel, EmailStr, Field, UUID4
from typing import Optional
from datetime import timedelta

from app.database import get_db
from app.models.user import User, Role
from app.models.image import School
from app.core.security import verify_password, get_password_hash, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from app.core.dependencies import get_current_user, require_roles

router = APIRouter(prefix="/auth", tags=["auth"])

class UserResponse(BaseModel):
    user_id: UUID4
    email: str
    role: Role
    is_global: bool
    school_id: Optional[str]

    model_config = {"from_attributes": True}

class InviteRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: Role
    school_id: Optional[str] = None

class CommunitySignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    school_id: str
    community_id_number: Optional[str] = None

# 1. Login endpoint (for everyone)
@router.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalars().first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.user_id), "role": user.role.value}, expires_delta=access_token_expires
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": str(user.user_id),
        "email": user.email,
        "role": user.role.value,
        "is_global": user.is_global,
        "school_id": user.school_id
    }

# 2. Get current user profile
@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

# 3. Invite high-level accounts (Admin only)
@router.post("/invite", response_model=UserResponse)
async def invite_user(
    body: InviteRequest, 
    db: AsyncSession = Depends(get_db),
    # Only District Officer can invite new management or surveyors
    current_user: User = Depends(require_roles([Role.DISTRICT_OFFICER]))
):
    # Check if email exists
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Email already registered")

    is_global = body.role in [Role.DISTRICT_OFFICER, Role.SURVEYOR]
    
    if not is_global and not body.school_id:
        raise HTTPException(status_code=400, detail="School ID is required for School Management")

    if body.school_id:
        school = await db.get(School, body.school_id)
        if not school:
            raise HTTPException(status_code=404, detail="School not found")

    new_user = User(
        email=body.email,
        hashed_password=get_password_hash(body.password),
        role=body.role,
        is_global=is_global,
        school_id=body.school_id
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

# 4. Community Signup
@router.post("/signup/community", response_model=UserResponse)
async def community_signup(body: CommunitySignupRequest, db: AsyncSession = Depends(get_db)):
    # Check if email exists
    result = await db.execute(select(User).where(User.email == body.email))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Email already registered")

    school = await db.get(School, body.school_id)
    if not school:
        raise HTTPException(status_code=404, detail="Invalid School ID")

    new_user = User(
        email=body.email,
        hashed_password=get_password_hash(body.password),
        role=Role.COMMUNITY,
        is_global=False,
        school_id=body.school_id,
        community_id_number=body.community_id_number
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user
