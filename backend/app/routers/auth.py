"""Auth router — register and login."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.auth import RegisterRequest, LoginRequest, AuthResponse, UserOut
from app.middleware.auth import hash_password, verify_password, create_access_token

router = APIRouter()


@router.post("/register", response_model=AuthResponse, status_code=201)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check existing email
    existing = await db.execute(select(User).where(User.email == req.email))
    if existing.scalars().first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Email already registered")

    # Check existing username
    existing = await db.execute(select(User).where(User.username == req.username))
    if existing.scalars().first():
        raise HTTPException(status.HTTP_409_CONFLICT, "Username already taken")

    user = User(
        username=req.username,
        email=req.email,
        password_hash=hash_password(req.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_access_token(str(user.id))
    return AuthResponse(
        access_token=token,
        user=UserOut(
            id=str(user.id),
            username=user.username,
            email=user.email,
            created_at=user.created_at,
        ),
    )


@router.post("/login", response_model=AuthResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalars().first()

    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")

    token = create_access_token(str(user.id))
    return AuthResponse(
        access_token=token,
        user=UserOut(
            id=str(user.id),
            username=user.username,
            email=user.email,
            created_at=user.created_at,
        ),
    )
