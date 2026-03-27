from domain.entities import PyObjectId
from domain.repositories.user import IUserRepository


class UserService:
    def __init__(self, repo: IUserRepository):
        self.repo = repo

    async def basic_sign_in(self, name: str):
        return await self.repo.basic_sign_in(name)

    async def get_user_by_id(self, user_id: PyObjectId):
        return await self.repo.get_user_by_id(user_id)

    async def update_user_profile(self, user_id: str, name: str):
        return await self.repo.update_user_profile(user_id=user_id, name=name)

    async def update_favorite_property(
        self, user_id: str, property_id: PyObjectId, is_favorite: bool
    ):
        return await self.repo.update_favorite_property(
            user_id=user_id,
            property_id=property_id,
            is_favorite=is_favorite,
        )
