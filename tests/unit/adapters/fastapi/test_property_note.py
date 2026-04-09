import logging
from datetime import UTC, datetime

from application.dto.property import PropertyOverviewDto
from application.dto.property_note import UserPropertyNoteListPageDto
from domain.entities.property_note import PropertyNoteEntity
from interface.api.dependencies.property_note import get_property_note_service
from interface.api.dependencies.property import get_property_service
from interface.api.dependencies.user import get_current_user


class PropertyNoteServiceStub:
    def __init__(self, note=None, notes=None):
        self.note = note
        self.notes = notes or []
        self.calls = []

    async def get_note(self, user_id: str, property_id: str):
        self.calls.append(
            {"fn": "get_note", "user_id": user_id, "property_id": property_id}
        )
        return self.note

    async def save_note(self, user_id: str, property_id: str, content: str):
        self.calls.append(
            {
                "fn": "save_note",
                "user_id": user_id,
                "property_id": property_id,
                "content": content,
            }
        )
        return self.note

    async def delete_note(self, user_id: str, property_id: str):
        self.calls.append(
            {"fn": "delete_note", "user_id": user_id, "property_id": property_id}
        )
        return True

    async def list_notes(
        self, user_id: str, page: int, size: int, query: str | None = None
    ):
        self.calls.append(
            {
                "fn": "list_notes",
                "user_id": user_id,
                "page": page,
                "size": size,
                "query": query,
            }
        )
        return self.notes, len(self.notes)

    async def list_user_note_overviews(
        self,
        *,
        current_user,
        notes,
        total: int,
        page: int,
        size: int,
        property_overviews,
    ):
        self.calls.append(
            {
                "fn": "list_user_note_overviews",
                "current_user_id": str(current_user.id),
                "note_ids": [note.property_id for note in notes],
                "total": total,
                "page": page,
                "size": size,
                "property_ids": [item.id for item in property_overviews],
            }
        )
        favorite_property_ids = set(current_user.favorite_property_ids)
        items = [
            {
                "property_id": note.property_id,
                "content": note.content,
                "created_at": note.created_at,
                "updated_at": note.updated_at,
                "property": next(
                    (
                        item
                        for item in property_overviews
                        if item.id == note.property_id
                    ),
                    None,
                ),
            }
            for note in notes
        ]
        items.sort(key=lambda item: item["property_id"] not in favorite_property_ids)
        return UserPropertyNoteListPageDto(
            items=items,
            total=total,
            page=page,
            size=size,
            pages=(total + size - 1) // size if size else 0,
        )


class PropertyOverviewServiceStub:
    def __init__(self, properties=None):
        self.properties = properties or []
        self.calls = []

    async def get_overviews_by_ids(
        self, property_ids, current_user=None, note_first=False
    ):
        self.calls.append({"fn": "get_overviews_by_ids", "property_ids": property_ids})
        noted_property_ids = (
            {note.property_id for note in current_user.property_notes}
            if current_user is not None
            else set()
        )
        favorite_property_ids = (
            set(current_user.favorite_property_ids)
            if current_user is not None
            else set()
        )
        return [
            PropertyOverviewDto(
                id=item.id,
                name=item.name,
                address=item.address,
                latitude=item.latitude,
                longitude=item.longitude,
                category=item.category,
                types=item.types,
                rating=item.rating,
                is_open=item.is_open,
                has_note=item.id in noted_property_ids,
                is_favorite=item.id in favorite_property_ids,
            )
            for item in self.properties
        ]


def test_get_property_note_returns_note(client, override_api_dep, user_entity_factory):
    current_user = user_entity_factory(identifier="u1", name="Ben")
    note = PropertyNoteEntity(
        property_id="p1",
        content="hello",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        updated_at=datetime(2026, 1, 2, tzinfo=UTC),
    )
    service = override_api_dep(
        get_property_note_service, PropertyNoteServiceStub(note=note)
    )
    override_api_dep(get_current_user, current_user)

    response = client.get("/api/v1/property/p1/note")

    assert response.status_code == 200
    assert response.json()["content"] == "hello"
    assert service.calls == [{"fn": "get_note", "user_id": "u1", "property_id": "p1"}]


def test_get_property_note_returns_null_when_missing(
    client, override_api_dep, user_entity_factory
):
    current_user = user_entity_factory(identifier="u1", name="Ben")
    service = override_api_dep(
        get_property_note_service, PropertyNoteServiceStub(note=None)
    )
    override_api_dep(get_current_user, current_user)

    response = client.get("/api/v1/property/p1/note")

    assert response.status_code == 200
    assert response.json() is None
    assert service.calls == [{"fn": "get_note", "user_id": "u1", "property_id": "p1"}]


def test_put_property_note_upserts_note(
    client, override_api_dep, user_entity_factory, caplog
):
    current_user = user_entity_factory(identifier="u1", name="Ben")
    note = PropertyNoteEntity(
        property_id="p1",
        content="hello",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        updated_at=datetime(2026, 1, 2, tzinfo=UTC),
    )
    service = override_api_dep(
        get_property_note_service, PropertyNoteServiceStub(note=note)
    )
    override_api_dep(get_current_user, current_user)

    with caplog.at_level(logging.INFO, logger="interface.api.events"):
        response = client.put("/api/v1/property/p1/note", json={"content": "hello"})

    assert response.status_code == 200
    assert response.json()["property_id"] == "p1"
    assert service.calls == [
        {
            "fn": "save_note",
            "user_id": "u1",
            "property_id": "p1",
            "content": "hello",
        }
    ]
    record = next(
        record
        for record in caplog.records
        if record.event == "user_property_note_upserted"
    )
    assert record.user_id == "u1"
    assert record.resource == {"type": "property", "id": "p1"}
    assert record.is_created is True
    assert record.content_length == 5


def test_delete_property_note_returns_deleted_status(
    client, override_api_dep, user_entity_factory
):
    current_user = user_entity_factory(identifier="u1", name="Ben")
    service = override_api_dep(get_property_note_service, PropertyNoteServiceStub())
    override_api_dep(get_current_user, current_user)

    response = client.delete("/api/v1/property/p1/note")

    assert response.status_code == 200
    assert response.json() == {"property_id": "p1", "deleted": True}
    assert service.calls == [
        {"fn": "delete_note", "user_id": "u1", "property_id": "p1"}
    ]


def test_get_user_property_notes_returns_note_list_with_properties(
    client, override_api_dep, user_entity_factory, property_entity_factory, caplog
):
    note = PropertyNoteEntity(
        property_id="p1",
        content="hello",
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        updated_at=datetime(2026, 1, 2, tzinfo=UTC),
    )
    favorite_note = PropertyNoteEntity(
        property_id="p2",
        content="favorite",
        created_at=datetime(2026, 1, 3, tzinfo=UTC),
        updated_at=datetime(2026, 1, 4, tzinfo=UTC),
    )
    current_user = user_entity_factory(
        identifier="u1",
        name="Ben",
        favorite_property_ids=["p2"],
        property_notes=[note, favorite_note],
    )
    note_service = override_api_dep(
        get_property_note_service, PropertyNoteServiceStub(notes=[note, favorite_note])
    )
    property_service = override_api_dep(
        get_property_service,
        PropertyOverviewServiceStub(
            properties=[
                property_entity_factory(identifier="p1", name="Cafe 1"),
                property_entity_factory(identifier="p2", name="Cafe 2"),
            ]
        ),
    )
    override_api_dep(get_current_user, current_user)

    with caplog.at_level(logging.INFO, logger="interface.api.events"):
        response = client.get(
            "/api/v1/user/property-notes", params={"page": 1, "size": 20}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert [item["property_id"] for item in data["items"]] == ["p2", "p1"]
    assert data["items"][0]["content"] == "favorite"
    assert data["items"][0]["property"]["id"] == "p2"
    assert data["items"][0]["property"]["has_note"] is True
    assert data["items"][0]["property"]["is_favorite"] is True
    assert data["items"][1]["property"]["is_favorite"] is False
    assert note_service.calls == [
        {"fn": "list_notes", "user_id": "u1", "page": 1, "size": 20, "query": None},
        {
            "fn": "list_user_note_overviews",
            "current_user_id": "u1",
            "note_ids": ["p1", "p2"],
            "total": 2,
            "page": 1,
            "size": 20,
            "property_ids": ["p1", "p2"],
        },
    ]
    assert property_service.calls == [
        {"fn": "get_overviews_by_ids", "property_ids": ["p1", "p2"]}
    ]
    record = next(
        record
        for record in caplog.records
        if record.event == "user_property_notes_viewed"
    )
    assert record.user_id == "u1"
    assert record.note_count == 2


def test_get_user_property_notes_passes_query_and_handles_empty_results(
    client, override_api_dep, user_entity_factory
):
    current_user = user_entity_factory(identifier="u1", name="Ben")
    note_service = override_api_dep(
        get_property_note_service, PropertyNoteServiceStub(notes=[])
    )
    property_service = override_api_dep(
        get_property_service, PropertyOverviewServiceStub(properties=[])
    )
    override_api_dep(get_current_user, current_user)

    response = client.get(
        "/api/v1/user/property-notes",
        params={"page": 1, "size": 20, "query": "cat"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "total": 0,
        "page": 1,
        "size": 20,
        "pages": 0,
    }
    assert note_service.calls == [
        {"fn": "list_notes", "user_id": "u1", "page": 1, "size": 20, "query": "cat"},
        {
            "fn": "list_user_note_overviews",
            "current_user_id": "u1",
            "note_ids": [],
            "total": 0,
            "page": 1,
            "size": 20,
            "property_ids": [],
        },
    ]
    assert property_service.calls == [
        {"fn": "get_overviews_by_ids", "property_ids": []}
    ]
