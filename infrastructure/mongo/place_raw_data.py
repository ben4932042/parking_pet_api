import logging

from domain.entities.enrichment import AnalysisSource
from domain.repositories.place_raw_data import IPlaceRawDataRepository


logger = logging.getLogger(__name__)


class PlaceRawDataRepository(IPlaceRawDataRepository):
    def __init__(self, client, collection_name: str):
        self.collection = client.get_collection(collection_name)

    async def create(self, source: AnalysisSource):
        await self.collection.insert_one(source.model_dump(by_alias=True))

    async def save(self, source: AnalysisSource):
        await self.collection.replace_one(
            {"_id": source.id},
            source.model_dump(by_alias=True),
            upsert=True,
        )
