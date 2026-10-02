"""Run locally with:  uvicorn app.main:create_app --factory --reload"""

import datetime as dt
from collections.abc import Callable

from fastapi import FastAPI
from sqlalchemy.orm import sessionmaker

from engine import ENGINE_VERSION

from .config import Settings
from .db import Base, make_engine
from .routers import body, me, profile, training


def create_app(settings: Settings | None = None, clock: Callable[[], dt.datetime] | None = None) -> FastAPI:
    settings = settings or Settings()
    engine = make_engine(settings.database_url)
    if settings.create_tables:
        Base.metadata.create_all(engine)

    app = FastAPI(title="Distributed Volume Coach API", version=ENGINE_VERSION)
    app.state.settings = settings
    app.state.engine = engine
    app.state.sessionmaker = sessionmaker(engine, expire_on_commit=False)
    app.state.clock = clock or (lambda: dt.datetime.now(dt.UTC))

    for module in (profile, training, body, me):
        app.include_router(module.router)

    @app.get("/health", tags=["ops"])
    def health():
        return {"status": "ok", "engine_version": ENGINE_VERSION, "auth_mode": settings.auth_mode}

    return app
