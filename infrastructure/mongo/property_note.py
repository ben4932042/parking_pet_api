from datetime import UTC, datetime
from typing import Optional

from domain.entities.property_note import PropertyNoteEntity
from domain.repositories.property_note import IPropertyNoteRepository


class PropertyNoteRepository(IPropertyNoteRepository):
    def __init__(self, client, collection_name: str):
        self.collection = client.get_collection(collection_name)

    async def get_by_user_and_property(
        self, user_id: str, property_id: str
    ) -> Optional[PropertyNoteEntity]:
        doc = await self.collection.find_one(
            {"user_id": user_id, "property_id": property_id}
        )
        if doc:
            return PropertyNoteEntity(**doc)
        return None

    async def upsert(
        self, user_id: str, property_id: str, content: str
    ) -> PropertyNoteEntity:
        now = datetime.now(UTC)
        await self.collection.update_one(
            {"user_id": user_id, "property_id": property_id},
            {
                "$set": {"content": content, "updated_at": now},
                "$setOnInsert": {
                    "user_id": user_id,
                    "property_id": property_id,
                    "created_at": now,
                },
            },
            upsert=True,
        )
        note = await self.get_by_user_and_property(user_id, property_id)
        if note is None:
            raise RuntimeError("Failed to persist property note")
        return note

    async def delete(self, user_id: str, property_id: str) -> bool:
        result = await self.collection.delete_one(
            {"user_id": user_id, "property_id": property_id}
        )
        return result.deleted_count > 0

    async def list_by_user(
        self, user_id: str, page: int, size: int, query: str | None = None
    ) -> tuple[list[PropertyNoteEntity], int]:
        filters: dict = {"user_id": user_id}
        if query:
            filters["content"] = {"$regex": query, "$options": "i"}

        total = await self.collection.count_documents(filters)
        skip = max(0, (page - 1) * size)
        cursor = (
            self.collection.find(filters).sort("updated_at", -1).skip(skip).limit(size)
        )
        docs = await cursor.to_list(length=size)
        return [PropertyNoteEntity(**doc) for doc in docs], total

    async def get_noted_property_ids(
        self, user_id: str, property_ids: list[str]
    ) -> set[str]:
        if not property_ids:
            return set()
        rows = await self.collection.distinct(
            "property_id",
            {
                "user_id": user_id,
                "property_id": {"$in": property_ids},
            },
        )
        return set(rows)
