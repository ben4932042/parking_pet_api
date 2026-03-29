from abc import ABC, abstractmethod

from domain.entities.audit import PropertyAuditLog


class IPropertyAuditRepository(ABC):
    @abstractmethod
    async def create(self, audit_log: PropertyAuditLog) -> PropertyAuditLog:
        ...

    @abstractmethod
    async def list_by_property_id(self, property_id: str, limit: int = 50) -> list[PropertyAuditLog]:
        ...
