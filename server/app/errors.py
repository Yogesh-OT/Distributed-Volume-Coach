from fastapi import HTTPException


def api_error(status: int, code: str, message: str, **extra) -> HTTPException:
    """Errors carry a stable `code` for the app to branch on and a `message` to show."""
    return HTTPException(status_code=status, detail={"code": code, "message": message, **extra})
