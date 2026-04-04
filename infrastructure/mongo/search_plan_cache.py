from datetime import UTC, datetime

from pymongo import ReturnDocument

from domain.entities.search_plan_cache import SearchPlanCacheEntity
from domain.repositories.search_plan_cache import ISearchPlanCacheRepository
from infrastructure.mongo import MongoDBClient


class SearchPlanCacheRepository(ISearchPlanCacheRepository):
    def __init__(self, client: MongoDBClient, collection_name: str):
        self.collection = client.get_collection(collection_name)

    async def get_by_key(self, cache_key: str) -> SearchPlanCacheEntity | None:
        doc = await self.collection.find_one({"cache_key": cache_key})
        if doc is None:
            return None
        doc.pop("_id", None)
        return SearchPlanCacheEntity(**doc)

    async def save(self, entry: SearchPlanCacheEntity) -> SearchPlanCacheEntity:
        now = datetime.now(UTC)
        existing = await self.get_by_key(entry.cache_key)
        created_at = existing.created_at if existing is not None else now
        payload = entry.model_dump()
        payload["created_at"] = created_at
        payload["updated_at"] = now
        await self.collection.update_one(
            {"cache_key": entry.cache_key},
            {"$set": payload},
            upsert=True,
        )
        return SearchPlanCacheEntity(**payload)

    async def touch(self, cache_key: str) -> SearchPlanCacheEntity | None:
        now = datetime.now(UTC)
        doc = await self.collection.find_one_and_update(
            {"cache_key": cache_key},
            {"$set": {"updated_at": now}, "$inc": {"hit_count": 1}},
            return_document=ReturnDocument.AFTER,
        )
        if doc is None:
            return None
        doc.pop("_id", None)
        return SearchPlanCacheEntity(**doc)
