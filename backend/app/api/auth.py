from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr

from app.db.database import get_db
from app.db.models import User
from app.core.security import verify_password, get_password_hash, create_access_token, require_admin, get_current_user
from app.core.limiter import limiter

router = APIRouter(prefix="/auth", tags=["Authentication"])

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str

class AdminUserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    role: str = "Analyst"  # Admin, Analyst, Viewer

class RoleUpdate(BaseModel):
    role: str  # Admin, Analyst, Viewer

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    full_name: str

@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalars().first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"}
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User account is deactivated")
    
    access_token = create_access_token(subject=user.email, role=user.role)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user.role,
        "full_name": user.full_name
    }

@router.post("/register", response_model=TokenResponse)
@limiter.limit("10/minute")
async def register(request: Request, user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    """
    Public registration endpoint.
    ALWAYS assigns 'Viewer' role to prevent privilege escalation.
    """
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="User with this email already exists")

    public_role = "Viewer"
    new_user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        role=public_role,
        is_active=True
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    access_token = create_access_token(subject=new_user.email, role=public_role)
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": public_role,
        "full_name": new_user.full_name
    }

@router.post("/users", status_code=status.HTTP_201_CREATED)
async def create_user_by_admin(
    user_in: AdminUserCreate,
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_admin)
):
    """Admin-only endpoint to create users with explicit roles (Admin, Analyst, Viewer)."""
    result = await db.execute(select(User).where(User.email == user_in.email))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="User with this email already exists")

    target_role = user_in.role if user_in.role in ["Admin", "Analyst", "Viewer"] else "Viewer"
    new_user = User(
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        full_name=user_in.full_name,
        role=target_role,
        is_active=True
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return {"id": new_user.id, "email": new_user.email, "role": new_user.role, "message": "User created by admin."}

@router.put("/users/{user_id}/role")
async def promote_user_role(
    user_id: str,
    role_in: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    admin=Depends(require_admin)
):
    """Admin-only endpoint to promote/update a user's role."""
    if role_in.role not in ["Admin", "Analyst", "Viewer"]:
        raise HTTPException(status_code=400, detail="Invalid role specified")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.role = role_in.role
    await db.commit()
    return {"message": f"User '{user.email}' role updated to '{user.role}'."}

@router.get("/me")
async def read_current_user(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "is_active": current_user.is_active
    }
