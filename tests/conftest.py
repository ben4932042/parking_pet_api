# ruff: noqa: E402

import sys
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from domain.entities.property import OpeningPeriod, PropertyEntity, TimePoint
from domain.entities.user import UserEntity
from interface.api.exceptions.exception_handlers import register_exception_handlers
from interface.api.routes.v1 import router as v1_router
from interface.api.routes.v2 import router as v2_router
from domain.entities.audit import ActorInfo
from domain.entities.enrichment import (
    AIAnalysis,
    PetEnvironment,
    PetFeatures,
    PetRules,
    PetService,
)


@pytest.fixture
def api_app():
    app = FastAPI()
    app.include_router(v1_router, prefix="/api/v1")
    app.include_router(v2_router, prefix="/api/v2")
    register_exception_handlers(app)
    return app


@pytest.fixture
def client(api_app):
    return TestClient(api_app)


@pytest.fixture
def override_api_dep(api_app):
    overrides = []

    def _apply(dependency, instance):
        async def _dep():
            return instance

        api_app.dependency_overrides[dependency] = _dep
        overrides.append(dependency)
        return instance

    yield _apply

    for dependency in overrides:
        api_app.dependency_overrides.pop(dependency, None)


@pytest.fixture
def actor_factory():
    def _create(**kwargs):
        default = {
            "user_id": "u1",
            "name": "Ben",
            "role": "user",
            "source": "user",
        }
        default.update(kwargs)
        return ActorInfo(**default)

    return _create


@pytest.fixture
def property_entity_factory():
    def _create(
        *,
        identifier: str = "p1",
        place_id: str | None = None,
        latitude: float = 25.03,
        longitude: float = 121.56,
        rating: float = 4.0,
        primary_type: str = "cafe",
        is_open: bool = True,
        pet_menu: bool = False,
        free_water: bool = False,
        allow_on_floor: bool = False,
        spacious: bool = False,
        deleted: bool = False,
        name: str | None = None,
    ):
        entity = PropertyEntity(
            _id=identifier,
            name=name or identifier,
            place_id=place_id or identifier,
            latitude=latitude,
            longitude=longitude,
            regular_opening_hours=[
                OpeningPeriod(
                    open=TimePoint(day=0, hour=0, minute=0),
                    close=TimePoint(day=6, hour=23, minute=59),
                )
            ],
            address="Test address",
            primary_type=primary_type,
            ai_analysis=AIAnalysis(
                venue_type="pet-friendly cafe",
                ai_summary="summary",
                pet_features=PetFeatures(
                    rules=PetRules(
                        leash_required=False,
                        stroller_required=False,
                        allow_on_floor=allow_on_floor,
                    ),
                    environment=PetEnvironment(
                        stairs=False,
                        outdoor_seating=False,
                        spacious=spacious,
                        indoor_ac=True,
                        off_leash_possible=False,
                        pet_friendly_floor=True,
                        has_shop_pet=False,
                    ),
                    services=PetService(
                        pet_menu=pet_menu,
                        free_water=free_water,
                        free_treats=False,
                        pet_seating=False,
                    ),
                ),
                highlights=["friendly"],
                warnings=[],
                rating=rating,
            ),
            is_deleted=deleted,
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        entity.is_open = is_open
        return entity

    return _create


@pytest.fixture
def user_entity_factory():
    def _create(
        *,
        identifier: str = "u1",
        name: str = "Ben",
        source: str = "basic",
        favorite_property_ids: list[str] | None = None,
    ):
        return UserEntity(
            _id=identifier,
            name=name,
            source=source,
            favorite_property_ids=favorite_property_ids or [],
            created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            updated_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )

    return _create
