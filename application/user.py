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