from sqlalchemy.orm import Session

from backend.models.user_profile import UserProfile
from backend.schemas.user_profile import UserProfileCreate, UserProfileUpdate


PROFILE_ID = 1


def get_profile(db: Session) -> UserProfile | None:
    return db.query(UserProfile).filter(UserProfile.id == PROFILE_ID).first()


def create_profile(db: Session, profile_data: UserProfileCreate) -> UserProfile:
    profile = UserProfile(id=PROFILE_ID, **profile_data.model_dump())
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def update_profile(
    db: Session,
    profile: UserProfile,
    profile_data: UserProfileUpdate,
) -> UserProfile:
    for field, value in profile_data.model_dump(exclude_unset=True).items():
        if field in {"interests", "learning_goals", "personal_goals"} and value is None:
            value = []
        setattr(profile, field, value)

    db.commit()
    db.refresh(profile)
    return profile