from datetime import UTC, datetime
from typing import Optional

from bson import ObjectId

from domain.entities import PyObjectId
from domain.entities.property_note import PropertyNoteEntity
from domain.entities.user import UserEntity, UserSearchRecord
from domain.repositories.user import IUserRepository

RECENT_SEARCH_LIMIT = 20


class UserRepository(IUserRepository):
    def __init__(self, client, collection_name: str):
        self.collection = client.get_collection(collection_name)

    async def register_guest_user(
        self, name: str, pet_name: str | None = None
    ) -> UserEntity:
        now = datetime.now(UTC)
        result = await self.collection.insert_one(
            {
                "name": name,
                "pet_name": pet_name,
                "source": "guest",
                "favorite_property_ids": [],
                "property_notes": [],
                "recent_searches": [],
                "session_version": 0,
                "refresh_token_hash": None,
                "is_deleted": False,
                "deleted_at": None,
                "created_at": now,
                "updated_at": now,
            }
        )
        return UserEntity(
            _id=result.inserted_id,
            name=name,
            pet_name=pet_name,
            source="guest",
            favorite_property_ids=[],
            property_notes=[],
            recent_searches=[],
            session_version=0,
            refresh_token_hash=None,
            is_deleted=False,
            deleted_at=None,
            created_at=now,
            updated_at=now,
        )

    async def register_apple_user(
        self,
        *,
        apple_user_identifier: str,
        name: str,
        pet_name: str | None = None,
        email: str | None = None,
    ) -> UserEntity:
        now = datetime.now(UTC)
        result = await self.collection.insert_one(
            {
                "name": name,
                "pet_name": pet_name,
                "email": email,
                "source": "apple",
                "apple_user_identifier": apple_user_identifier,
                "favorite_property_ids": [],
                "property_notes": [],
                "recent_searches": [],
                "session_version": 0,
                "refresh_token_hash": None,
                "is_deleted": False,
                "deleted_at": None,
                "created_at": now,
                "updated_at": now,
            }
        )
        return UserEntity(
            _id=result.inserted_id,
            name=name,
            pet_name=pet_name,
            email=email,
            source="apple",
            apple_user_identifier=apple_user_identifier,
            favorite_property_ids=[],
            property_notes=[],
            recent_searches=[],
            session_version=0,
            refresh_token_hash=None,
            is_deleted=False,
            deleted_at=None,
            created_at=now,
            updated_at=now,
        )

    async def get_user_by_id(self, user_id: PyObjectId) -> Optional[UserEntity]:
        doc = await self.collection.find_one({"_id": ObjectId(user_id)})
        if doc:
            return UserEntity(**doc)
        return None

    async def get_user_by_apple_user_identifier(
        self, apple_user_identifier: str
    ) -> Optional[UserEntity]:
        doc = await self.collection.find_one(
            {"apple_user_identifier": apple_user_identifier}
        )
        if doc:
            return UserEntity(**doc)
        return None

    async def link_guest_user_to_apple(
        self,
        *,
        user_id: str,
        apple_user_identifier: str,
        email: str | None = None,
    ) -> UserEntity | None:
        now = datetime.now(UTC)
        update_fields = {
            "source": "apple",
            "apple_user_identifier": apple_user_identifier,
            "updated_at": now,
        }
        if email is not None:
            update_fields["email"] = email
        await self.collection.update_one(
            {"_id": ObjectId(user_id), "source": "guest", "is_deleted": False},
            {"$set": update_fields},
        )
        doc = await self.collection.find_one(
            {"_id": ObjectId(user_id), "source": "apple", "is_deleted": False}
        )
        if doc:
            return UserEntity(**doc)
        return None

    async def update_user_profile(
        self,
        user_id: str,
        name: str,
        pet_name: str | None = None,
    ) -> UserEntity:
        await self.collection.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"name": name, "pet_name": pet_name}},
        )
        return await self.get_user_by_id(user_id)

    async def update_favorite_property(
        self, user_id: str, property_id: PyObjectId, is_favorite: bool
    ) -> UserEntity:
        operator = "$addToSet" if is_favorite else "$pull"
        await self.collection.update_one(
            {"_id": ObjectId(user_id)},
            {operator: {"favorite_property_ids": str(property_id)}},
        )
        return await self.get_user_by_id(user_id)

    async def get_property_note(
        self, user_id: str, property_id: str
    ) -> PropertyNoteEntity | None:
        user = await self.get_user_by_id(user_id)
        if user is None:
            return None
        return next(
            (note for note in user.property_notes if note.property_id == property_id),
            None,
        )

    async def upsert_property_note(
        self, user_id: str, property_id: str, content: str
    ) -> PropertyNoteEntity:
        user = await self.get_user_by_id(user_id)
        now = datetime.now(UTC)
        if user is None:
            raise RuntimeError("User not found")

        notes = list(user.property_notes)
        existing_note = next(
            (note for note in notes if note.property_id == property_id),
            None,
        )
        if existing_note is None:
            notes.append(
                PropertyNoteEntity(
                    property_id=property_id,
                    content=content,
                    created_at=now,
                    updated_at=now,
                )
            )
        else:
            existing_note.content = content
            existing_note.updated_at = now

        await self.collection.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "property_notes": [note.model_dump(mode="json") for note in notes],
                    "updated_at": now,
                }
            },
        )
        return next(note for note in notes if note.property_id == property_id)

    async def delete_property_note(self, user_id: str, property_id: str) -> bool:
        user = await self.get_user_by_id(user_id)
        if user is None:
            return False

        notes = [
            note for note in user.property_notes if note.property_id != property_id
        ]
        deleted = len(notes) != len(user.property_notes)
        if not deleted:
            return False

        await self.collection.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "property_notes": [note.model_dump(mode="json") for note in notes],
                    "updated_at": datetime.now(UTC),
                }
            },
        )
        return True

    async def list_property_notes(
        self, user_id: str, page: int, size: int, query: str | None = None
    ) -> tuple[list[PropertyNoteEntity], int]:
        user = await self.get_user_by_id(user_id)
        if user is None:
            return [], 0

        notes = list(user.property_notes)
        if query:
            normalized_query = query.lower()
            notes = [note for note in notes if normalized_query in note.content.lower()]

        notes.sort(key=lambda note: note.updated_at, reverse=True)
        total = len(notes)
        skip = max(0, (page - 1) * size)
        return notes[skip : skip + size], total

    async def record_recent_search(
        self,
        user_id: str,
        query: str,
        *,
        limit: int = RECENT_SEARCH_LIMIT,
    ) -> UserEntity:
        user = await self.get_user_by_id(user_id)
        if user is None:
            return None

        normalized_query = query.strip()
        records = [
            record
            for record in user.recent_searches
            if record.query.strip() != normalized_query
        ]
        records.insert(
            0,
            UserSearchRecord(
                query=normalized_query,
                searched_at=datetime.now(UTC),
            ),
        )
        trimmed_records = records[: max(1, min(limit, 50))]

        await self.collection.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "recent_searches": [
                        record.model_dump(mode="json") for record in trimmed_records
                    ],
                    "updated_at": datetime.now(UTC),
                }
            },
        )
        return await self.get_user_by_id(user_id)

    async def delete_user(self, user_id: PyObjectId) -> bool:
        now = datetime.now(UTC)
        result = await self.collection.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "is_deleted": True,
                    "deleted_at": now,
                    "updated_at": now,
                }
            },
        )
        return result.matched_count > 0

    async def restore_user(self, user_id: PyObjectId) -> UserEntity | None:
        now = datetime.now(UTC)
        await self.collection.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "is_deleted": False,
                    "deleted_at": None,
                    "updated_at": now,
                }
            },
        )
        return await self.get_user_by_id(user_id)

    async def start_auth_session(
        self,
        *,
        user_id: str,
        refresh_token_hash: str,
    ) -> UserEntity | None:
        await self.collection.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "refresh_token_hash": refresh_token_hash,
                    "updated_at": datetime.now(UTC),
                },
                "$inc": {"session_version": 1},
            },
        )
        return await self.get_user_by_id(user_id)

    async def rotate_refresh_token(
        self,
        *,
        user_id: str,
        refresh_token_hash: str,
    ) -> UserEntity | None:
        await self.collection.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "refresh_token_hash": refresh_token_hash,
                    "updated_at": datetime.now(UTC),
                }
            },
        )
        return await self.get_user_by_id(user_id)

    async def revoke_auth_session(self, *, user_id: str) -> UserEntity | None:
        await self.collection.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "refresh_token_hash": None,
                    "updated_at": datetime.now(UTC),
                },
                "$inc": {"session_version": 1},
            },
        )
        return await self.get_user_by_id(user_id)
