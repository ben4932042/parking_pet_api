from domain.entities import PyObjectId
from domain.repositories.property import IPropertyRepository


class PropertyService:
    def __init__(self, repo: IPropertyRepository):
        self.repo = repo

    def search_properties(self, lat, lng, radius, q, type):
        # 這裡可以加入 NLP 處理邏輯，解析 q 裡面的關鍵字
        return self.repo.get_nearby(lat, lng, radius, q, type)

    def get_details(self, property_id: PyObjectId):
        return self.repo.get_property_by_id(property_id)

    def update_favorite(self, user_id: str, property_id: PyObjectId, is_favorite: bool):
        return self.repo.toggle_favorite(user_id, property_id, is_favorite)