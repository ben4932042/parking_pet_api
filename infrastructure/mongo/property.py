from typing import Optional, List

from bson import ObjectId

from domain.entities import PyObjectId
from domain.entities.property import PropertyEntity
from domain.repositories.property import IPropertyRepository

class PropertyRepository(IPropertyRepository):
    def __init__(self, client, collection_name: str):
        self.collection = client.get_collection(collection_name)

    def _map_doc_to_entity(self, doc: dict) -> PropertyEntity:

        raw_types = doc.get("types", "")
        if isinstance(raw_types, str):
            types_list = [t.strip() for t in raw_types.split(",") if t.strip()]
        else:
            types_list = raw_types if isinstance(raw_types, list) else []

        raw_tags = (
            (doc.get("ai_analysis") or {}).get("suitable_for") or doc.get("tags") or ""
        )
        if isinstance(raw_tags, str):
            tags_list = [t.strip() for t in raw_tags.split(",") if t.strip()]
        else:
            tags_list = raw_tags if isinstance(raw_tags, list) else []

        ai_analysis = doc.get("ai_analysis") or {}
        ai_summary = ai_analysis.get("ai_summary", doc.get("ai_summary", ""))

        mapped_data = {
            "id": str(doc.get("_id")),
            "name": doc.get("display_name")
            or doc.get("original_search_name")
            or "未命名地點",
            "address": doc.get("address", ""),
            "latitude": float(doc.get("lat", 0.0)),
            "longitude": float(doc.get("lng", 0.0)),
            "types": types_list,
            "rating": float(doc.get("rating", 0.0)),
            "tags": tags_list,
            "ai_summary": ai_summary,
            "parking_score": 0,
            "is_favorite": False,
        }

        return PropertyEntity(**mapped_data)

    async def get_nearby(self, lat: float, lng: float, radius: int, q: Optional[str], type: Optional[str], limit: int = 100) -> List[PropertyEntity]:
        cursor = self.collection.find({
            "location": {
                "$near": {
                    "$geometry": {
                        "type": "Point",
                        "coordinates": [lng, lat]
                    },
                    "$maxDistance": radius
                }
            }
        })

        docs = await cursor.to_list(length=limit)
        return [self._map_doc_to_entity(doc) for doc in docs]

    async def get_property_by_id(self, property_id: PyObjectId) -> Optional[PropertyEntity]:
        doc = await self.collection.find_one({"_id": ObjectId(property_id)})
        if doc:
            return self._map_doc_to_entity(doc)
        return None

    async def toggle_favorite(self, user_id: str, property_id: PyObjectId, is_favorite: bool) -> bool:
        print("Not implemented yet. =)")