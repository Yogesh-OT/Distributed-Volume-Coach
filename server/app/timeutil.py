import datetime as dt
from zoneinfo import ZoneInfo

from fastapi import Request

from .errors import api_error
from .models import User


def user_today(request: Request, user: User) -> dt.date:
    """The user's local calendar date, using the app's injectable clock."""
    now: dt.datetime = request.app.state.clock()
    return now.astimezone(ZoneInfo(user.timezone)).date()


def require_near_today(request: Request, user: User, day: dt.date) -> None:
    tolerance = request.app.state.settings.date_tolerance_days
    today = user_today(request, user)
    if abs((day - today).days) > tolerance:
        raise api_error(422, "date_out_of_range", f"The date must be within {tolerance} day of today ({today}).")
