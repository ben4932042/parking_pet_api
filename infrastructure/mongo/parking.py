from datetime import UTC, datetime

from domain.entities.parking import ParkingEntity
from domain.repositories.parking import IParkingRepository


class ParkingRepository(IParkingRepository):
    def __init__(self, client, collection_name: str):
        self.collection = client.get_collection(collection_name)

    async def save(self, parking: ParkingEntity) -> ParkingEntity:
        existing = await self.collection.find_one({"_id": parking.id})
        now = datetime.now(UTC)
        created_at = (
            existing.get("created_at", now) if existing is not None else parking.created_at
        )
        payload = parking.model_copy(
            update={
                "created_at": created_at,
                "updated_at": now,
            }
        )
        await self.collection.replace_one(
            {"_id": payload.id},
            payload.model_dump(by_alias=True),
            upsert=True,
        )
        return payload
