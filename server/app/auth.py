from functools import lru_cache

from fastapi import Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import get_db
from .errors import api_error
from .models import User


def get_auth_uid(request: Request, authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise api_error(401, "unauthenticated", "Sign in first.")
    token = authorization.removeprefix("Bearer ").strip()

    if request.app.state.settings.auth_mode == "dev":
        # Keep the prefix so a dev user can never collide with a real Firebase uid.
        if not token.startswith("dev:") or len(token) < 5:
            raise api_error(401, "unauthenticated", "Dev mode expects 'Bearer dev:<id>'.")
        return token
    return _verify_firebase_token(token)


@lru_cache(maxsize=1)
def _firebase_app():
    import firebase_admin  # imported lazily: only installed with the "prod" extra

    # Reads credentials from GOOGLE_APPLICATION_CREDENTIALS.
    return firebase_admin.initialize_app()


def _verify_firebase_token(token: str) -> str:
    from firebase_admin import auth

    try:
        decoded = auth.verify_id_token(token, app=_firebase_app())
    except (ValueError, auth.InvalidIdTokenError) as exc:
        raise api_error(401, "unauthenticated", "Your sign-in has expired. Sign in again.") from exc
    return decoded["uid"]


def current_user(uid: str = Depends(get_auth_uid), db: Session = Depends(get_db)) -> User:
    user = db.scalar(select(User).where(User.auth_uid == uid))
    if user is None:
        raise api_error(404, "not_onboarded", "Finish onboarding first.")
    return user
