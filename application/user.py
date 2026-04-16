"""Application service for user profile and preference workflows."""

from domain.entities import PyObjectId
from domain.repositories.user import IUserRepository


class UserService:
    """Coordinates user-facing application flows backed by the user repository."""

    def __init__(self, repo: IUserRepository):
        self.repo = repo

    async def register_guest_user(self, name: str, pet_name: str | None = None):
        """Create a guest user account with optional pet profile data."""
        return await self.repo.register_guest_user(name=name, pet_name=pet_name)

    async def get_user_by_id(self, user_id: PyObjectId):
        """Load a user by repository identifier."""
        return await self.repo.get_user_by_id(user_id)

    async def update_user_profile(
        self,
        user_id: str,
        name: str,
        pet_name: str | None = None,
    ):
        """Persist profile updates for the current user."""
        return await self.repo.update_user_profile(
            user_id=user_id,
            name=name,
            pet_name=pet_name,
        )

    async def update_favorite_property(
        self, user_id: str, property_id: PyObjectId, is_favorite: bool
    ):
        """Add or remove a property from the user's favorites."""
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
        """Append a query to the user's recent-search history with a max size."""
        return await self.repo.record_recent_search(
            user_id=user_id,
            query=query,
            limit=limit,
        )

    async def delete_user(self, user_id: PyObjectId) -> bool:
        """Soft-delete a user account through the repository contract."""
        return await self.repo.delete_user(user_id)
