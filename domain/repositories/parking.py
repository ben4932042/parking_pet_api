from abc import ABC, abstractmethod

from domain.entities.parking import ParkingEntity


class IParkingRepository(ABC):
    @abstractmethod
    async def save(self, parking: ParkingEntity) -> ParkingEntity: ...
