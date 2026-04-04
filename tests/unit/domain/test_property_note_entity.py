import pytest
from pydantic import ValidationError

from domain.entities.property_note import PropertyNoteEntity


def test_property_note_entity_trims_content():
    note = PropertyNoteEntity(property_id="p1", content="  hello note  ")

    assert note.content == "hello note"


def test_property_note_entity_rejects_blank_content():
    with pytest.raises(ValidationError) as exc_info:
        PropertyNoteEntity(property_id="p1", content="   ")

    assert "Note content cannot be empty." in str(exc_info.value)
