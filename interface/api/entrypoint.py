import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from interface.api.lifespan import lifespan
from interface.api.middlewares.logging import LoggingMiddleware
from interface.api.routes.v1 import router as v1_router
from infrastructure.config import settings

logger = logging.getLogger(__name__)

def get_app():
    app = FastAPI(title="Parking Pet API", lifespan=lifespan)
    app.add_middleware(
        LoggingMiddleware, exclude_paths=("/docs", "/openapi.json")
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(v1_router, prefix="/api/v1", tags=["v1"])

    logger.info(f"Config: {settings.model_dump(exclude_none=True)}")
    return app
