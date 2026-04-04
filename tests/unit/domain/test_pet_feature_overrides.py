from domain.entities.property import (
    PetEnvironmentOverride,
    PetFeaturesOverride,
    PetRulesOverride,
    PetServiceOverride,
    PropertyEntity,
    PropertyManualOverrides,
)


def test_pet_features_override_merge_into_only_updates_specified_fields(
    property_entity_factory,
):
    inferred = property_entity_factory(
        allow_on_floor=False,
        free_water=False,
        pet_menu=True,
        spacious=False,
    ).ai_analysis.pet_features

    override = PetFeaturesOverride(
        rules=PetRulesOverride(allow_on_floor=True),
        services=PetServiceOverride(free_water=True),
        environment=PetEnvironmentOverride(spacious=True),
    )

    merged = override.merge_into(inferred)

    assert merged.rules.allow_on_floor is True
    assert merged.rules.leash_required is False
    assert merged.environment.spacious is True
    assert merged.environment.indoor_ac is True
    assert merged.services.free_water is True
    assert merged.services.pet_menu is True


def test_property_entity_generates_effective_pet_features_from_manual_overrides(
    property_entity_factory,
):
    base_entity = property_entity_factory(
        identifier="p1",
        allow_on_floor=False,
        free_water=False,
        pet_menu=True,
    )

    entity = PropertyEntity(
        **base_entity.model_dump(by_alias=True, exclude_none=True),
        manual_overrides=PropertyManualOverrides(
            pet_features=PetFeaturesOverride(
                rules=PetRulesOverride(allow_on_floor=True),
                services=PetServiceOverride(free_water=True),
            )
        ),
    )

    assert entity.effective_pet_features.rules.allow_on_floor is True
    assert entity.effective_pet_features.services.free_water is True
    assert entity.effective_pet_features.services.pet_menu is True
