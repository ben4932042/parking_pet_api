from datetime import UTC, datetime

from pymongo import MongoClient

from domain.entities.landmark_cache import LandmarkCacheEntity
from domain.repositories.landmark_cache import ILandmarkCacheRepository
from infrastructure.config import settings


class LandmarkCacheRepository(ILandmarkCacheRepository):
    def __init__(self, collection_name: str):
        client = MongoClient(settings.mongo.url.get_secret_value())
        database = client[settings.mongo.db_name]
        self.collection = database[collection_name]
        self.collection.create_index("cache_key", unique=True)

    def get_by_key(self, cache_key: str) -> LandmarkCacheEntity | None:
        doc = self.collection.find_one({"cache_key": cache_key})
        if doc is None:
            return None
        doc.pop("_id", None)
        return LandmarkCacheEntity(**doc)

    def save(self, entry: LandmarkCacheEntity) -> LandmarkCacheEntity:
        now = datetime.now(UTC)
        existing = self.get_by_key(entry.cache_key)
        created_at = existing.created_at if existing is not None else now
        payload = entry.model_dump()
        payload["created_at"] = created_at
        payload["updated_at"] = now
        self.collection.update_one(
            {"cache_key": entry.cache_key},
            {"$set": payload},
            upsert=True,
        )
        return LandmarkCacheEntity(**payload)
