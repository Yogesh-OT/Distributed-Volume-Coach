from fastapi import APIRouter, Depends, Response
from sqlalchemy import delete, inspect, select
from sqlalchemy.orm import Session

from ..auth import current_user
from ..db import get_db
from ..models import USER_TABLES, User

router = APIRouter(prefix="/v1/me", tags=["account"])


def _row(obj) -> dict:
    out = {}
    for column in inspect(obj).mapper.column_attrs:
        value = getattr(obj, column.key)
        out[column.key] = value.isoformat() if hasattr(value, "isoformat") else value
    return out


@router.get("/export")
def export_my_data(user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Everything stored about the signed-in user, as JSON."""
    data = {"user": _row(user)}
    for model in USER_TABLES:
        rows = db.scalars(select(model).where(model.user_id == user.id)).all()
        data[model.__tablename__] = [_row(r) for r in rows]
    return data


@router.delete("", status_code=204)
def delete_my_account(user: User = Depends(current_user), db: Session = Depends(get_db)):
    for model in USER_TABLES:
        db.execute(delete(model).where(model.user_id == user.id))
    db.execute(delete(User).where(User.id == user.id))
    db.commit()
    return Response(status_code=204)
