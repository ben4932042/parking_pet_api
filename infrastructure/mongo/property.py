from typing import Optional, List, Tuple
import logging
import re
from bson import ObjectId

from domain.entities import PyObjectId
from domain.entities.property import PropertyEntity
from domain.repositories.property import IPropertyRepository

logger = logging.getLogger(__name__)

DEFAULT_SEARCH_LIMIT = 100
DEFAULT_QUERY_MAX_TIME_MS = 5000


class PropertyRepository(IPropertyRepository):
    def __init__(self, client, collection_name: str):
        self.collection = client.get_collection(collection_name)

    @staticmethod
    def _active_filter() -> dict:
        return {"is_deleted": {"$ne": True}}

    def _merge_active_filter(self, query: dict | None = None) -> dict:
        base_filter = self._active_filter()
        if not query:
            return base_filter
        return {"$and": [base_filter, query]}

    @staticmethod
    def _build_variant_regex(text: str) -> str:
        pattern_parts: list[str] = []
        for char in text:
            if char in {"台", "臺"}:
                pattern_parts.append("[台臺]")
            else:
                pattern_parts.append(re.escape(char))
        return "".join(pattern_parts)

    @classmethod
    def _normalize_regex_query(cls, value):
        if isinstance(value, dict):
            normalized: dict = {}
            for key, item in value.items():
                if key == "$regex" and isinstance(item, str):
                    normalized[key] = cls._build_variant_regex(item)
                else:
                    normalized[key] = cls._normalize_regex_query(item)
            return normalized
        if isinstance(value, list):
            return [cls._normalize_regex_query(item) for item in value]
        return value

    async def get_by_keyword(self, q: str) -> List[PropertyEntity]:
        regex = self._build_variant_regex(q)
        filters = {
            "$or": [
                {"name": {"$regex": regex, "$options": "i"}},
                {"address": {"$regex": regex, "$options": "i"}},
            ]
        }
        logger.debug(
            "Mongo keyword query",
            extra={
                "query_text": q,
                "mongo_query": self._merge_active_filter(filters),
            },
        )
        cursor = (
            self.collection.find(self._merge_active_filter(filters))
            .limit(DEFAULT_SEARCH_LIMIT)
            .max_time_ms(DEFAULT_QUERY_MAX_TIME_MS)
        )
        docs = await cursor.to_list(length=DEFAULT_SEARCH_LIMIT)
        items = [PropertyEntity(**doc) for doc in docs]
        return items

    async def find_by_query(self, query: dict) -> List[PropertyEntity]:
        normalized_query = self._normalize_regex_query(query)
        logger.debug("Mongo semantic query", extra={"mongo_query": normalized_query})
        cursor = (
            self.collection.find(self._merge_active_filter(normalized_query))
            .sort("rating", -1)
            .limit(DEFAULT_SEARCH_LIMIT)
            .max_time_ms(DEFAULT_QUERY_MAX_TIME_MS)
        )
        docs = await cursor.to_list(length=DEFAULT_SEARCH_LIMIT)
        return [PropertyEntity(**doc) for doc in docs]

    async def get_nearby(
        self,
        lat: float,
        lng: float,
        radius: int,
        types: List[str],
        page: int,
        size: int,
    ) -> Tuple[List[PropertyEntity], int]:
        filters = {}

        if types:
            filters["primary_type"] = {"$in": types}

        geo_filter = {
            "location": {
                "$near": {
                    "$geometry": {"type": "Point", "coordinates": [lng, lat]},
                    "$maxDistance": radius,
                }
            }
        }
        filters.update(geo_filter)

        count_filter = filters.copy()
        if "location" in count_filter:
            count_filter["location"] = {
                "$geoWithin": {"$centerSphere": [[lng, lat], radius / 6378100]}
            }

        count_filter = self._merge_active_filter(count_filter)
        total: int = await self.collection.count_documents(count_filter)

        skip = max(0, (page - 1) * size)
        cursor = (
            self.collection.find(self._merge_active_filter(filters))
            .skip(skip)
            .limit(size)
        )

        docs = await cursor.to_list(length=size)
        items = []
        try:
            for doc in docs:
                item = PropertyEntity(**doc)
                items.append(item)
        except Exception:
            logger.exception(f"Error processing document: {doc}", exc_info=True)

        return items, total

    async def get_property_by_id(
        self, property_id: PyObjectId, include_deleted: bool = False
    ) -> Optional[PropertyEntity]:
        query = {"_id": property_id}
        if not include_deleted:
            query = self._merge_active_filter(query)
        doc = await self.collection.find_one(query)
        if doc:
            return PropertyEntity(**doc)
        return None

    async def get_property_by_place_id(
        self,
        place_id: str,
        include_deleted: bool = False,
    ) -> Optional[PropertyEntity]:
        query = {"place_id": place_id}
        if not include_deleted:
            query = self._merge_active_filter(query)
        doc = await self.collection.find_one(query)
        if doc:
            return PropertyEntity(**doc)
        return None

    async def get_properties_by_ids(
        self, property_ids: List[str]
    ) -> List[PropertyEntity]:
        if not property_ids:
            return []

        object_ids: List[ObjectId] = []
        for property_id in property_ids:
            if ObjectId.is_valid(property_id):
                object_ids.append(ObjectId(property_id))

        query_values = list(property_ids) + object_ids
        docs = await self.collection.find(
            self._merge_active_filter({"_id": {"$in": query_values}})
        ).to_list(length=len(query_values))
        entity_map = {str(doc["_id"]): PropertyEntity(**doc) for doc in docs}
        return [
            entity_map[property_id]
            for property_id in property_ids
            if property_id in entity_map
        ]

    async def create(self, new_property: PropertyEntity):
        await self.collection.insert_one(new_property.model_dump(by_alias=True))

    async def save(self, property_entity: PropertyEntity) -> PropertyEntity:
        payload = property_entity.model_dump(by_alias=True)
        await self.collection.replace_one(
            {"_id": property_entity.id}, payload, upsert=True
        )
        return property_entity
