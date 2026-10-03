"""Testing helpers. Only mounted when DVC_AUTH_MODE=dev, so they don't exist in production."""

import datetime as dt

from fastapi import APIRouter, Depends, Response
from sqlalchemy import delete
from sqlalchemy.orm import Session

from ..auth import current_user
from ..db import get_db
from ..models import Checkin, Plan, SetLog, User

router = APIRouter(prefix="/v1/dev", tags=["dev"])


@router.delete("/days/{day}", status_code=204)
def reset_day(day: dt.date, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Forget one day's check-in, plan and set logs, so the day can be planned again."""
    for model in (SetLog, Plan, Checkin):
        db.execute(delete(model).where(model.user_id == user.id, model.date == day))
    db.commit()
    return Response(status_code=204)
