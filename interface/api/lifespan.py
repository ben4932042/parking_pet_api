import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI


from infrastructure.mongo import MongoDBClient

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    mongodb_client = MongoDBClient()

    _ = mongodb_client.get_client()
    logger.debug("Successfully connected to MongoDB")

    yield

    await mongodb_client.close()
    logger.info("Application shutdown completed successfully")
