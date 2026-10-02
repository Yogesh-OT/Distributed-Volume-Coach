from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from engine.body import BodyInput, body_profile

from ..auth import current_user
from ..db import get_db
from ..errors import api_error
from ..models import BodyMeasurement, User
from ..schemas import BodyMeasurementIn, BodyProfileOut, ProfileLineOut
from .profile import latest_profile

router = APIRouter(prefix="/v1", tags=["body"])

FIELDS = ("height_cm", "weight_kg", "arm_span_cm", "waist_cm", "wrist_cm")


def _build_profile(db: Session, user: User) -> BodyProfileOut:
    rows = db.scalars(
        select(BodyMeasurement)
        .where(BodyMeasurement.user_id == user.id)
        .order_by(BodyMeasurement.measured_on.desc(), BodyMeasurement.id.desc())
    ).all()
    if not rows:
        raise api_error(404, "no_measurements", "Add your measurements to see your body profile.")

    # Each value comes from the most recent measurement that included it, so a
    # weekly weigh-in doesn't need the tape-measure numbers again.
    latest = {f: next((getattr(r, f) for r in rows if getattr(r, f) is not None), None) for f in FIELDS}
    lines = body_profile(BodyInput(**latest, sex=latest_profile(db, user).sex))
    return BodyProfileOut(
        measured_on=rows[0].measured_on,
        lines=[ProfileLineOut(**line.__dict__) for line in lines],
    )


@router.post("/body-measurements", status_code=201, response_model=BodyProfileOut)
def add_measurements(body: BodyMeasurementIn, user: User = Depends(current_user), db: Session = Depends(get_db)):
    db.add(BodyMeasurement(user_id=user.id, **body.model_dump()))
    db.commit()
    return _build_profile(db, user)


@router.get("/body-profile", response_model=BodyProfileOut)
def get_body_profile(user: User = Depends(current_user), db: Session = Depends(get_db)):
    return _build_profile(db, user)
