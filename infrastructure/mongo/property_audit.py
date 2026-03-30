from domain.entities.audit import PropertyAuditLog
from domain.repositories.property_audit import IPropertyAuditRepository


class PropertyAuditRepository(IPropertyAuditRepository):
    def __init__(self, client, collection_name: str):
        self.collection = client.get_collection(collection_name)

    async def create(self, audit_log: PropertyAuditLog) -> PropertyAuditLog:
        payload = audit_log.model_dump(by_alias=True, exclude_none=True)
        result = await self.collection.insert_one(payload)
        return audit_log.model_copy(update={"id": str(result.inserted_id)})

    async def list_by_property_id(
        self, property_id: str, limit: int = 50
    ) -> list[PropertyAuditLog]:
        cursor = (
            self.collection.find({"property_id": property_id})
            .sort("created_at", -1)
            .limit(limit)
        )
        docs = await cursor.to_list(length=limit)
        return [PropertyAuditLog(**doc) for doc in docs]
