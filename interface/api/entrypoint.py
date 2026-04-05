import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from interface.api.exceptions.exception_handlers import register_exception_handlers
from interface.api.lifespan import lifespan
from interface.api.middlewares.logging import LoggingMiddleware
from interface.api.routes.v1 import router as v1_router
from infrastructure.config import settings
from infrastructure.monitoring.prometheus import register_runtime_metrics

logger = logging.getLogger(__name__)


def get_app():
    app = FastAPI(title="Parking Pet API", lifespan=lifespan)
    register_runtime_metrics()
    Instrumentator().instrument(app).expose(app, tags=["System"])
    app.add_middleware(
        LoggingMiddleware,
        exclude_paths=("/docs", "/openapi.json", "/metrics"),
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(v1_router, prefix="/api/v1")
    register_exception_handlers(app)
    logger.info(f"Config: {settings.model_dump(exclude_none=True)}")
    return app
