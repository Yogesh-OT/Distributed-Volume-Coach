from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from engine.safety import is_adult

from ..auth import current_user, get_auth_uid
from ..db import get_db
from ..errors import api_error
from ..models import Consent, Profile, User
from ..schemas import OnboardingIn, OnboardingOut, ProfileIn, ProfileOut
from ..timeutil import user_today

router = APIRouter(prefix="/v1", tags=["profile"])


def latest_profile(db: Session, user: User) -> Profile:
    profile = db.scalar(
        select(Profile).where(Profile.user_id == user.id).order_by(Profile.version.desc()).limit(1)
    )
    if profile is None:  # onboarding always creates version 1
        raise api_error(404, "not_onboarded", "Finish onboarding first.")
    return profile


@router.post("/onboarding", status_code=201, response_model=OnboardingOut)
def onboard(body: OnboardingIn, request: Request, uid: str = Depends(get_auth_uid), db: Session = Depends(get_db)):
    if db.scalar(select(User).where(User.auth_uid == uid)) is not None:
        raise api_error(409, "already_onboarded", "This account has already finished onboarding.")
    if not body.accepted_terms:
        raise api_error(422, "terms_required", "Accept the terms to continue.")

    user = User(auth_uid=uid, timezone=body.timezone, birth_year=body.birth_year)
    if not is_adult(body.birth_year, user_today(request, user), body.confirmed_adult):
        raise api_error(403, "adults_only", "Distributed Volume Coach is for people aged 18 and over.")

    db.add(user)
    db.flush()
    db.add(Consent(user_id=user.id, kind="terms"))
    profile = Profile(user_id=user.id, version=1, **body.profile.model_dump())
    db.add(profile)
    db.commit()
    return OnboardingOut(user_id=user.id, profile=ProfileOut.model_validate(profile))


@router.get("/profile", response_model=ProfileOut)
def get_profile(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return latest_profile(db, user)


@router.put("/profile", response_model=ProfileOut)
def update_profile(body: ProfileIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    previous = latest_profile(db, user)
    profile = Profile(user_id=user.id, version=previous.version + 1, **body.model_dump())
    db.add(profile)
    db.commit()
    return profile
