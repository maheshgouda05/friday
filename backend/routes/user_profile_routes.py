from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas.user_profile import (
    UserProfileCreate,
    UserProfileRead,
    UserProfileUpdate,
)
from backend.services import user_profile_service


router = APIRouter(prefix="/profile", tags=["User Profile"])


@router.post("", response_model=UserProfileRead, status_code=status.HTTP_201_CREATED)
def create_profile(
    profile_data: UserProfileCreate,
    db: Session = Depends(get_db),
):
    if user_profile_service.get_profile(db) is not None:
        raise HTTPException(status_code=409, detail="User profile already exists")
    return user_profile_service.create_profile(db, profile_data)


@router.get("", response_model=UserProfileRead)
def get_profile(db: Session = Depends(get_db)):
    profile = user_profile_service.get_profile(db)
    if profile is None:
        raise HTTPException(status_code=404, detail="User profile not found")
    return profile


@router.patch("", response_model=UserProfileRead)
def update_profile(
    profile_data: UserProfileUpdate,
    db: Session = Depends(get_db),
):
    profile = user_profile_service.get_profile(db)
    if profile is None:
        raise HTTPException(status_code=404, detail="User profile not found")
    return user_profile_service.update_profile(db, profile, profile_data)