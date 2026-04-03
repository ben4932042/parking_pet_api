from domain.entities import PyObjectId
from domain.repositories.user import IUserRepository


class UserService:
    def __init__(self, repo: IUserRepository):
        self.repo = repo

    async def register_basic_user(self, name: str, pet_name: str | None = None):
        return await self.repo.register_basic_user(name=name, pet_name=pet_name)

    async def get_user_by_id(self, user_id: PyObjectId):
        return await self.repo.get_user_by_id(user_id)

    async def update_user_profile(
        self,
        user_id: str,
        name: str,
        pet_name: str | None = None,
    ):
        return await self.repo.update_user_profile(
            user_id=user_id,
            name=name,
            pet_name=pet_name,
        )

    async def update_favorite_property(
        self, user_id: str, property_id: PyObjectId, is_favorite: bool
    ):
        return await self.repo.update_favorite_property(
            user_id=user_id,
            property_id=property_id,
            is_favorite=is_favorite,
        )

    async def record_recent_search(
        self,
        *,
        user_id: str,
        query: str,
        limit: int = 20,
    ):
        return await self.repo.record_recent_search(
            user_id=user_id,
            query=query,
            limit=limit,
        )

    async def delete_user(self, user_id: PyObjectId) -> bool:
        return await self.repo.delete_user(user_id)
