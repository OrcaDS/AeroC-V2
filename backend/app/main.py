from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config.settings import settings
from app.api.router import api_router
from app.runtime.collection_runner import CollectionRunner
from app.runtime.collection_scheduler import CollectionScheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


def create_collection_scheduler() -> CollectionScheduler:
    return CollectionScheduler(
        runner=CollectionRunner(),
        interval_minutes=settings.COLLECTION_INTERVAL_MINUTES,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = None

    if settings.SCHEDULER_ENABLED:
        scheduler = create_collection_scheduler()
        scheduler.start()
        app.state.collection_scheduler = scheduler

    try:
        yield
    finally:
        if scheduler is not None:
            scheduler.shutdown()

app = FastAPI(
    title="AeroC API",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(api_router, prefix="/api/v1")

