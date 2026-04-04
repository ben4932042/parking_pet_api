from datetime import UTC, datetime

import pytest

from application.exceptions import NotFoundError, ValidationDomainError
from application.property_note import PropertyNoteService
from domain.entities.property_note import PropertyNoteEntity
from domain.repositories.property import IPropertyRepository
from domain.repositories.user import IUserRepository


class PropertyRepoStub(IPropertyRepository):
    def __init__(self, property_entity=None):
        self.property_entity = property_entity
        self.calls = []

    async def get_by_keyword(self, q):
        raise NotImplementedError

    async def get_nearby(self, lat, lng, radius, types, page, size):
        raise NotImplementedError

    async def get_property_by_id(self, property_id, include_deleted=False):
        self.calls.append(
            {
                "fn": "get_property_by_id",
                "property_id": property_id,
                "include_deleted": include_deleted,
            }
        )
        return self.property_entity

    async def get_property_by_place_id(self, place_id, include_deleted=False):
        raise NotImplementedError

    async def get_properties_by_ids(self, property_ids):
        raise NotImplementedError

    async def create(self, new_property):
        raise NotImplementedError

    async def find_by_query(self, query, open_at_minutes=None):
        raise NotImplementedError

    async def save(self, property_entity):
        raise NotImplementedError


class UserRepoStub(IUserRepository):
    def __init__(self, note=None, notes=None):
        self.note = note
        self.notes = notes or ([] if note is None else [note])
        self.calls = []

    async def register_basic_user(self, name: str, pet_name: str | None = None):
        raise NotImplementedError

    async def register_apple_user(
        self,
        *,
        apple_user_identifier: str,
        name: str,
        pet_name: str | None = None,
        email: str | None = None,
    ):
        raise NotImplementedError

    async def get_user_by_id(self, user_id: str):
        raise NotImplementedError

    async def get_user_by_apple_user_identifier(self, apple_user_identifier: str):
        raise NotImplementedError

    async def update_user_profile(
        self, user_id: str, name: str, pet_name: str | None = None
    ):
        raise NotImplementedError

    async def update_favorite_property(
        self, user_id: str, property_id: str, is_favorite: bool
    ):
        raise NotImplementedError

    async def get_property_note(self, user_id: str, property_id: str):
        self.calls.append(
            {
                "fn": "get_property_note",
                "user_id": user_id,
                "property_id": property_id,
            }
        )
        return self.note

    async def upsert_property_note(self, user_id: str, property_id: str, content: str):
        self.calls.append(
            {
                "fn": "upsert_property_note",
                "user_id": user_id,
                "property_id": property_id,
                "content": content,
            }
        )
        self.note = PropertyNoteEntity(
            property_id=property_id,
            content=content,
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
            updated_at=datetime(2026, 1, 2, tzinfo=UTC),
        )
        return self.note

    async def delete_property_note(self, user_id: str, property_id: str):
        self.calls.append(
            {
                "fn": "delete_property_note",
                "user_id": user_id,
                "property_id": property_id,
            }
        )
        return True

    async def list_property_notes(
        self, user_id: str, page: int, size: int, query: str | None = None
    ):
        self.calls.append(
            {
                "fn": "list_property_notes",
                "user_id": user_id,
                "page": page,
                "size": size,
                "query": query,
            }
        )
        return self.notes, len(self.notes)

    async def record_recent_search(self, user_id: str, query: str, *, limit: int = 20):
        raise NotImplementedError

    async def delete_user(self, user_id: str):
        raise NotImplementedError

    async def restore_user(self, user_id: str):
        raise NotImplementedError

    async def start_auth_session(self, *, user_id: str, refresh_token_hash: str):
        raise NotImplementedError

    async def rotate_refresh_token(self, *, user_id: str, refresh_token_hash: str):
        raise NotImplementedError

    async def revoke_auth_session(self, *, user_id: str):
        raise NotImplementedError


@pytest.mark.asyncio
async def test_get_note_returns_repo_note_after_property_check(property_entity_factory):
    note = PropertyNoteEntity(
        property_id="p1",
        content="hello",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        updated_at=datetime(2026, 1, 2, tzinfo=UTC),
    )
    property_repo = PropertyRepoStub(property_entity_factory(identifier="p1"))
    user_repo = UserRepoStub(note=note)
    service = PropertyNoteService(user_repo=user_repo, property_repo=property_repo)

    result = await service.get_note("u1", "p1")

    assert result == note
    assert property_repo.calls == [
        {
            "fn": "get_property_by_id",
            "property_id": "p1",
            "include_deleted": False,
        }
    ]
    assert user_repo.calls == [
        {"fn": "get_property_note", "user_id": "u1", "property_id": "p1"}
    ]


@pytest.mark.asyncio
async def test_save_note_upserts_trimmed_content(property_entity_factory):
    property_repo = PropertyRepoStub(property_entity_factory(identifier="p1"))
    user_repo = UserRepoStub()
    service = PropertyNoteService(user_repo=user_repo, property_repo=property_repo)

    result = await service.save_note("u1", "p1", "  hello note  ")

    assert result.content == "hello note"
    assert property_repo.calls[0]["fn"] == "get_property_by_id"
    assert user_repo.calls[-1] == {
        "fn": "upsert_property_note",
        "user_id": "u1",
        "property_id": "p1",
        "content": "hello note",
    }


@pytest.mark.asyncio
async def test_save_note_raises_when_property_missing():
    service = PropertyNoteService(
        user_repo=UserRepoStub(),
        property_repo=PropertyRepoStub(property_entity=None),
    )

    with pytest.raises(NotFoundError):
        await service.save_note("u1", "missing", "hello")


@pytest.mark.asyncio
async def test_save_note_raises_for_blank_content(property_entity_factory):
    service = PropertyNoteService(
        user_repo=UserRepoStub(),
        property_repo=PropertyRepoStub(property_entity_factory(identifier="p1")),
    )

    with pytest.raises(ValidationDomainError):
        await service.save_note("u1", "p1", "   ")


@pytest.mark.asyncio
async def test_save_note_raises_for_content_over_limit(property_entity_factory):
    service = PropertyNoteService(
        user_repo=UserRepoStub(),
        property_repo=PropertyRepoStub(property_entity_factory(identifier="p1")),
    )

    with pytest.raises(ValidationDomainError):
        await service.save_note("u1", "p1", "a" * 2001)


@pytest.mark.asyncio
async def test_delete_note_delegates_after_property_check(property_entity_factory):
    property_repo = PropertyRepoStub(property_entity_factory(identifier="p1"))
    user_repo = UserRepoStub()
    service = PropertyNoteService(user_repo=user_repo, property_repo=property_repo)

    deleted = await service.delete_note("u1", "p1")

    assert deleted is True
    assert property_repo.calls == [
        {
            "fn": "get_property_by_id",
            "property_id": "p1",
            "include_deleted": False,
        }
    ]
    assert user_repo.calls == [
        {"fn": "delete_property_note", "user_id": "u1", "property_id": "p1"}
    ]


@pytest.mark.asyncio
async def test_list_notes_delegates_to_repo(property_entity_factory):
    note = PropertyNoteEntity(
        property_id="p1",
        content="hello",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        updated_at=datetime(2026, 1, 2, tzinfo=UTC),
    )
    user_repo = UserRepoStub(notes=[note])
    service = PropertyNoteService(
        user_repo=user_repo,
        property_repo=PropertyRepoStub(property_entity_factory(identifier="p1")),
    )

    notes, total = await service.list_notes("u1", page=1, size=20, query="hel")

    assert total == 1
    assert notes[0].property_id == "p1"
    assert user_repo.calls == [
        {
            "fn": "list_property_notes",
            "user_id": "u1",
            "page": 1,
            "size": 20,
            "query": "hel",
        }
    ]
