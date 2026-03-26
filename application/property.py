from typing import Optional

from domain.entities import PyObjectId
from domain.repositories.property import IPropertyRepository


class PropertyService:
    def __init__(self, repo: IPropertyRepository):
        self.repo = repo

    async def search_nearby(self, lat: float, lng: float, radius: int,  type: Optional[str], page: int, size: int):
        return await self.repo.get_nearby(lat, lng, radius, type, page, size)

    async def search_by_keyword(self, q: str, type: Optional[str], page: int, size: int):
        # 這裡可以加入 NLP 處理邏輯，解析 q 裡面的關鍵字
        return await self.repo.get_by_keyword(q, type, page, size)

    async def get_details(self, property_id: PyObjectId):
        return await self.repo.get_property_by_id(property_id)

    async def update_favorite(self, user_id: str, property_id: PyObjectId, is_favorite: bool):
        return await self.repo.toggle_favorite(user_id, property_id, is_favorite)