from datetime import UTC, datetime

import pytest

from application.exceptions import NotFoundError, ValidationDomainError
from application.property_note import PropertyNoteService
from domain.entities.property_note import PropertyNoteEntity
from domain.repositories.property import IPropertyRepository
from domain.repositories.property_note import IPropertyNoteRepository


class PropertyRepoStub(IPropertyRepository):
    def __init__(self, property_entity=None):
        self.property_entity = property_entity
        self.calls = []

    async def get_by_keyword(self, q):
        raise NotImplementedError

    async def get_nearby(self, lat, lng, radius, types, page, size):
        raise NotImplementedError

    async def search_by_vector(self, query_vector, limit=20, filters=None):
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


class PropertyNoteRepoStub(IPropertyNoteRepository):
    def __init__(self, note=None, notes=None):
        self.note = note
        self.notes = notes or ([] if note is None else [note])
        self.calls = []

    async def get_by_user_and_property(self, user_id: str, property_id: str):
        self.calls.append(
            {
                "fn": "get_by_user_and_property",
                "user_id": user_id,
                "property_id": property_id,
            }
        )
        return self.note

    async def upsert(self, user_id: str, property_id: str, content: str):
        self.calls.append(
            {
                "fn": "upsert",
                "user_id": user_id,
                "property_id": property_id,
                "content": content,
            }
        )
        self.note = PropertyNoteEntity(
            _id="n1",
            user_id=user_id,
            property_id=property_id,
            content=content,
            created_at=datetime(2026, 1, 1, tzinfo=UTC),
            updated_at=datetime(2026, 1, 2, tzinfo=UTC),
        )
        return self.note

    async def delete(self, user_id: str, property_id: str):
        self.calls.append(
            {
                "fn": "delete",
                "user_id": user_id,
                "property_id": property_id,
            }
        )
        return True

    async def list_by_user(
        self, user_id: str, page: int, size: int, query: str | None = None
    ):
        self.calls.append(
            {
                "fn": "list_by_user",
                "user_id": user_id,
                "page": page,
                "size": size,
                "query": query,
            }
        )
        return self.notes, len(self.notes)

    async def get_noted_property_ids(
        self, user_id: str, property_ids: list[str]
    ) -> set[str]:
        self.calls.append(
            {
                "fn": "get_noted_property_ids",
                "user_id": user_id,
                "property_ids": property_ids,
            }
        )
        return {
            note.property_id for note in self.notes if note.property_id in property_ids
        }


@pytest.mark.asyncio
async def test_save_note_upserts_trimmed_content(property_entity_factory):
    property_repo = PropertyRepoStub(property_entity_factory(identifier="p1"))
    note_repo = PropertyNoteRepoStub()
    service = PropertyNoteService(note_repo=note_repo, property_repo=property_repo)

    result = await service.save_note("u1", "p1", "  hello note  ")

    assert result.content == "hello note"
    assert property_repo.calls[0]["fn"] == "get_property_by_id"
    assert note_repo.calls[-1] == {
        "fn": "upsert",
        "user_id": "u1",
        "property_id": "p1",
        "content": "hello note",
    }


@pytest.mark.asyncio
async def test_save_note_raises_when_property_missing():
    service = PropertyNoteService(
        note_repo=PropertyNoteRepoStub(),
        property_repo=PropertyRepoStub(property_entity=None),
    )

    with pytest.raises(NotFoundError):
        await service.save_note("u1", "missing", "hello")


@pytest.mark.asyncio
async def test_save_note_raises_for_blank_content(property_entity_factory):
    service = PropertyNoteService(
        note_repo=PropertyNoteRepoStub(),
        property_repo=PropertyRepoStub(property_entity_factory(identifier="p1")),
    )

    with pytest.raises(ValidationDomainError):
        await service.save_note("u1", "p1", "   ")


@pytest.mark.asyncio
async def test_list_notes_delegates_to_repo(property_entity_factory):
    note = PropertyNoteEntity(
        _id="n1",
        user_id="u1",
        property_id="p1",
        content="hello",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        updated_at=datetime(2026, 1, 2, tzinfo=UTC),
    )
    note_repo = PropertyNoteRepoStub(notes=[note])
    service = PropertyNoteService(
        note_repo=note_repo,
        property_repo=PropertyRepoStub(property_entity_factory(identifier="p1")),
    )

    notes, total = await service.list_notes("u1", page=1, size=20, query="hel")

    assert total == 1
    assert notes[0].property_id == "p1"
    assert note_repo.calls == [
        {
            "fn": "list_by_user",
            "user_id": "u1",
            "page": 1,
            "size": 20,
            "query": "hel",
        }
    ]
