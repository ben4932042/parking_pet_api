import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI


from infrastructure.mongo import get_mongodb_client

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    mongodb_client = get_mongodb_client()

    _ = mongodb_client.get_client()
    await mongodb_client.get_collection("landmark_cache").create_index(
        "cache_key", unique=True
    )
    await mongodb_client.get_collection("search_plan_cache").create_index(
        "cache_key", unique=True
    )
    await mongodb_client.get_collection("parking").create_index(
        [("location", "2dsphere")]
    )
    logger.debug("Successfully connected to MongoDB")

    yield

    await mongodb_client.close()
    logger.info("Application shutdown completed successfully")
