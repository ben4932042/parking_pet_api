from typing import Optional, List, Tuple
import logging
from bson import ObjectId

from domain.entities import PyObjectId
from domain.entities.property import PropertyEntity
from domain.repositories.property import IPropertyRepository

logger = logging.getLogger(__name__)

class PropertyRepository(IPropertyRepository):
    def __init__(self, client, collection_name: str):
        self.collection = client.get_collection(collection_name)

    async def get_by_keyword(
        self,
        q: str,
        type: Optional[str],
        page: int,
        size: int,
    ) -> Tuple[List[PropertyEntity], int]:
        filters = {}
        if type:
            filters["types"] = {"$in": [type]}

        filters["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"address": {"$regex": q, "$options": "i"}},
        ]

        count_filter = filters.copy()

        total: int = await self.collection.count_documents(count_filter)

        skip = max(0, (page - 1) * size)
        cursor = self.collection.find(filters).skip(skip).limit(size)

        docs = await cursor.to_list(length=size)

        items = [PropertyEntity(**doc) for doc in docs]
        return items, total

    async def get_nearby(
        self,
        lat: float,
        lng: float,
        radius: int,
        type: Optional[str],
        page: int,
        size: int,
    ) -> Tuple[List[PropertyEntity], int]:
        filters = {}

        if type:
            filters["primary_type"] = {"$in": [type]}


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

        total: int = await self.collection.count_documents(count_filter)

        skip = max(0, (page - 1) * size)
        cursor = self.collection.find(filters).skip(skip).limit(size)

        docs = await cursor.to_list(length=size)
        items = []
        try:
            for doc in docs:
                item = PropertyEntity(**doc)
                items.append(item)
        except Exception as e:
            logger.exception(f"Error processing document: {doc}", exc_info=True)

        return items, total

    async def get_property_by_id(self, property_id: PyObjectId) -> Optional[PropertyEntity]:
        doc = await self.collection.find_one({"_id": property_id})
        if doc:
            return PropertyEntity(**doc)
        return None

    async def get_properties_by_ids(self, property_ids: List[str]) -> List[PropertyEntity]:
        if not property_ids:
            return []

        object_ids: List[ObjectId] = []
        for property_id in property_ids:
            if ObjectId.is_valid(property_id):
                object_ids.append(ObjectId(property_id))

        query_values = list(property_ids) + object_ids
        docs = await self.collection.find({"_id": {"$in": query_values}}).to_list(length=len(query_values))
        entity_map = {str(doc["_id"]): PropertyEntity(**doc) for doc in docs}
        return [entity_map[property_id] for property_id in property_ids if property_id in entity_map]

    async def create(self, new_property: PropertyEntity):
        await self.collection.insert_one(new_property.model_dump(by_alias=True))

