import logging
import math
from typing import Any, List, Optional

from domain.entities.audit import ActorInfo, PropertyAuditAction, PropertyAuditLog
from domain.entities import PyObjectId
from domain.entities.property import (
    PetEnvironmentOverride,
    PetFeaturesOverride,
    PetRulesOverride,
    PetServiceOverride,
    PropertyDetailEntity,
    PropertyEntity,
    PropertyManualOverrides,
)
from domain.repositories.place_raw_data import IPlaceRawDataRepository
from domain.repositories.property_audit import IPropertyAuditRepository
from domain.repositories.property_note import IPropertyNoteRepository
from domain.repositories.property import IPropertyRepository
from domain.services.property_enrichment import IEnrichmentProvider
from interface.api.exceptions.error import ConflictError, NotFoundError


logger = logging.getLogger(__name__)


PROMPT_INJECTION_ROUTE_REASON = "查詢包含 prompt injection 訊號，改用關鍵字搜尋"


class PropertyService:
    def __init__(
        self,
        repo: IPropertyRepository,
        raw_data_repo: IPlaceRawDataRepository,
        audit_repo: IPropertyAuditRepository,
        note_repo: IPropertyNoteRepository,
        enrichment_provider: IEnrichmentProvider,
    ):
        self.repo = repo
        self.raw_data_repo = raw_data_repo
        self.audit_repo = audit_repo
        self.note_repo = note_repo
        self.enrichment_provider = enrichment_provider

    async def search_nearby(
        self,
        lat: float,
        lng: float,
        radius: int,
        types: List[str],
        page: int,
        size: int,
    ):
        return await self.repo.get_nearby(lat, lng, radius, types, page, size)

    async def search_by_keyword(
        self,
        q: str,
        user_coords: Optional[tuple[float, float]] = None,
        map_coords: Optional[tuple[float, float]] = None,
        open_at_minutes: Optional[int] = None,
    ):
        search_plan = self.enrichment_provider.extract_search_plan(q)
        logger.debug(f"Search plan: {search_plan}")

        if search_plan.route == "keyword" or search_plan.used_fallback:
            if search_plan.route_reason == PROMPT_INJECTION_ROUTE_REASON:
                logger.warning(
                    "Blocked prompt-injection-like search query",
                    extra={"query_text": q, "route_reason": search_plan.route_reason},
                )
                return [], search_plan

            logger.debug(
                "Search using keyword fallback",
                extra={
                    "query_text": q,
                    "fallback_reason": search_plan.fallback_reason,
                    "warnings": search_plan.warnings,
                },
            )
            items = await self.repo.get_by_keyword(q)
            return items[:1], search_plan

        if self._travel_time_requires_geo_anchor(
            search_plan, user_coords=user_coords, map_coords=map_coords
        ):
            warning = "missing_geo_anchor_for_travel_time"
            if warning not in search_plan.warnings:
                search_plan.warnings.append(warning)
            logger.info(
                "Skipping semantic travel-time search without geo anchor",
                extra={
                    "query_text": q,
                    "travel_time_limit_min": search_plan.filter_condition.travel_time_limit_min,
                },
            )
            return [], search_plan

        generate_query = self.enrichment_provider.generate_query(
            search_plan.filter_condition,
            user_coords,
            map_coords,
        )
        logger.debug(
            "Generated query",
            extra={
                "query_text": q,
                "mongo_query": generate_query,
                "semantic_extraction": search_plan.semantic_extraction,
                "warnings": search_plan.warnings,
            },
        )
        items = await self.repo.find_by_query(
            generate_query, open_at_minutes=open_at_minutes
        )
        if not items:
            logger.info("Semantic search returned no results.")
            logger.debug(
                "Semantic query returned no results",
                extra={
                    "query_text": q,
                    "mongo_query": generate_query,
                },
            )
        else:
            items = self._rank_search_results(items, generate_query)
        return items, search_plan

    @staticmethod
    def _travel_time_requires_geo_anchor(
        search_plan,
        user_coords: Optional[tuple[float, float]] = None,
        map_coords: Optional[tuple[float, float]] = None,
    ) -> bool:
        condition = search_plan.filter_condition
        if condition.travel_time_limit_min is None:
            return False

        if condition.landmark_context == "CURRENT_LOCATION":
            return user_coords is None

        if condition.landmark_context:
            return False

        return user_coords is None and map_coords is None

    async def get_overviews_by_ids(self, property_ids: list[str]):
        return await self.repo.get_properties_by_ids(property_ids)

    async def get_noted_property_ids(
        self, user_id: str, property_ids: list[str]
    ) -> set[str]:
        return await self.note_repo.get_noted_property_ids(user_id, property_ids)

    async def get_details(
        self, property_id: PyObjectId
    ) -> Optional[PropertyDetailEntity]:
        output: PropertyEntity = await self.repo.get_property_by_id(property_id)
        if output is None:
            return None
        return self._to_detail_entity(output)

    async def create_property(self, name: str, actor: Optional[ActorInfo] = None):
        actor = actor or self._system_actor()
        source_data = self.enrichment_provider.create_property_by_name(name)
        if source_data is None:
            raise ValueError("Failed to resolve property from the provided keyword.")
        await self.raw_data_repo.save(source_data)
        existing = await self.repo.get_property_by_place_id(
            source_data.place_id, include_deleted=True
        )
        if existing and existing.is_deleted:
            raise ConflictError(
                "Property is soft-deleted. Restore it before syncing again."
            )

        ai_result = self.enrichment_provider.generate_ai_analysis(source_data)
        if ai_result is None:
            raise ValueError(
                "Failed to generate AI analysis for the resolved property."
            )
        if existing:
            final_property = self._merge_synced_property(existing, ai_result, actor)
            action = PropertyAuditAction.SYNC
            before = existing
        else:
            if ai_result.primary_type == "unknown":
                raise ValueError(
                    "Resolved property has unknown primary_type and cannot be created."
                )
            final_property = ai_result.model_copy(
                update={
                    "created_by": actor,
                    "updated_by": actor,
                }
            )
            action = PropertyAuditAction.CREATE
            before = None

        saved_property = await self.repo.save(final_property)
        await self._create_audit_log(
            property_id=saved_property.id,
            action=action,
            actor=actor,
            before=before,
            after=saved_property,
        )
        logging.info(f"Property {name} created successfully")
        return saved_property

    async def update_pet_features(
        self,
        property_id: PyObjectId,
        pet_rules: Optional[PetRulesOverride],
        pet_environment: Optional[PetEnvironmentOverride],
        pet_service: Optional[PetServiceOverride],
        actor: ActorInfo,
        reason: Optional[str] = None,
    ) -> PropertyDetailEntity:
        existing = await self.repo.get_property_by_id(property_id)
        if existing is None:
            raise NotFoundError("Property not found")

        override = PetFeaturesOverride(
            rules=pet_rules,
            environment=pet_environment,
            services=pet_service,
        )
        if not override.model_dump(exclude_none=True):
            raise ConflictError("At least one pet feature override must be provided.")

        merged_override = self._merge_pet_feature_overrides(
            existing.manual_overrides.pet_features
            if existing.manual_overrides
            else None,
            override,
        )
        updated_property = existing.model_copy(
            update={
                "manual_overrides": PropertyManualOverrides(
                    pet_features=merged_override,
                    updated_by=actor,
                    updated_at=self._now(),
                    reason=reason,
                ),
                "updated_by": actor,
                "updated_at": self._now(),
            }
        )
        updated_property = PropertyEntity(**updated_property.model_dump(by_alias=True))
        saved_property = await self.repo.save(updated_property)
        await self._create_audit_log(
            property_id=saved_property.id,
            action=PropertyAuditAction.PET_FEATURES_OVERRIDE,
            actor=actor,
            before=existing,
            after=saved_property,
            reason=reason,
        )
        return self._to_detail_entity(saved_property)

    async def soft_delete_property(
        self,
        property_id: PyObjectId,
        actor: ActorInfo,
        reason: Optional[str] = None,
    ) -> PropertyDetailEntity:
        existing = await self.repo.get_property_by_id(property_id, include_deleted=True)
        if existing is None:
            raise NotFoundError("Property not found")
        if existing.is_deleted:
            raise ConflictError("Property is already soft-deleted")

        updated_property = existing.model_copy(
            update={
                "is_deleted": True,
                "deleted_at": self._now(),
                "deleted_by": actor,
                "updated_at": self._now(),
                "updated_by": actor,
            }
        )
        updated_property = PropertyEntity(**updated_property.model_dump(by_alias=True))
        saved_property = await self.repo.save(updated_property)
        await self._create_audit_log(
            property_id=saved_property.id,
            action=PropertyAuditAction.SOFT_DELETE,
            actor=actor,
            before=existing,
            after=saved_property,
            reason=reason,
        )
        return self._to_detail_entity(saved_property)

    async def restore_property(
        self,
        property_id: PyObjectId,
        actor: ActorInfo,
        reason: Optional[str] = None,
    ) -> PropertyDetailEntity:
        existing = await self.repo.get_property_by_id(property_id, include_deleted=True)
        if existing is None:
            raise NotFoundError("Property not found")
        if not existing.is_deleted:
            raise ConflictError("Property is not deleted")

        updated_property = existing.model_copy(
            update={
                "is_deleted": False,
                "deleted_at": None,
                "deleted_by": None,
                "updated_at": self._now(),
                "updated_by": actor,
            }
        )
        updated_property = PropertyEntity(**updated_property.model_dump(by_alias=True))
        saved_property = await self.repo.save(updated_property)
        await self._create_audit_log(
            property_id=saved_property.id,
            action=PropertyAuditAction.RESTORE,
            actor=actor,
            before=existing,
            after=saved_property,
            reason=reason,
        )
        return self._to_detail_entity(saved_property)

    async def get_audit_logs(
        self, property_id: PyObjectId, limit: int = 50
    ) -> list[PropertyAuditLog]:
        existing = await self.repo.get_property_by_id(property_id, include_deleted=True)
        if existing is None:
            raise NotFoundError("Property not found")
        return await self.audit_repo.list_by_property_id(
            property_id=str(property_id), limit=limit
        )

    def _rank_search_results(
        self, items: List[PropertyEntity], query: dict
    ) -> List[PropertyEntity]:
        type_filter = query.get("primary_type")
        is_open_required = query.get("is_open") is True
        requested_feature_paths = self._requested_feature_paths(query)
        geo_context = self._extract_geo_context(query)

        return sorted(
            items,
            key=lambda item: self._score_search_result(
                item=item,
                type_filter=type_filter,
                is_open_required=is_open_required,
                requested_feature_paths=requested_feature_paths,
                geo_context=geo_context,
            ),
            reverse=True,
        )

    @staticmethod
    def _score_search_result(
        item: PropertyEntity,
        type_filter: Any,
        is_open_required: bool,
        requested_feature_paths: List[str],
        geo_context: Optional[dict[str, Any]],
    ) -> float:
        rating_score = max(0.0, min((item.ai_analysis.ai_rating or 0.0) / 5.0, 1.0))
        pet_feature_score = PropertyService._pet_feature_score(item)
        requested_feature_score = PropertyService._requested_feature_score(
            item, requested_feature_paths
        )
        distance_score = PropertyService._distance_score(item, geo_context)
        type_score = PropertyService._type_score(item, type_filter)
        open_score = 0.05 if is_open_required and item.is_open else 0.0

        return (
            (rating_score * 0.45)
            + (pet_feature_score * 0.20)
            + (requested_feature_score * 0.15)
            + (distance_score * 0.15)
            + type_score
            + open_score
        )

    @staticmethod
    def _type_score(item: PropertyEntity, type_filter: Any) -> float:
        if not type_filter:
            return 0.0

        if isinstance(type_filter, dict) and "$in" in type_filter:
            return 0.05 if item.primary_type in type_filter["$in"] else 0.0

        return 0.05 if item.primary_type == type_filter else 0.0

    @staticmethod
    def _pet_feature_score(item: PropertyEntity) -> float:
        pet_features = (
            item.effective_pet_features or item.ai_analysis.pet_features
        ).model_dump()
        bool_values: List[bool] = []

        def _collect(values: Any) -> None:
            if isinstance(values, dict):
                for nested in values.values():
                    _collect(nested)
            elif isinstance(values, bool):
                bool_values.append(values)

        _collect(pet_features)
        if not bool_values:
            return 0.0

        return sum(1 for value in bool_values if value) / len(bool_values)

    @staticmethod
    def _requested_feature_paths(query: dict) -> List[str]:
        return [
            key
            for key, value in query.items()
            if key.startswith("effective_pet_features.") and isinstance(value, bool)
        ]

    @staticmethod
    def _requested_feature_score(
        item: PropertyEntity, requested_feature_paths: List[str]
    ) -> float:
        if not requested_feature_paths:
            return 0.0

        matched = sum(
            1
            for path in requested_feature_paths
            if PropertyService._get_nested_value(item.model_dump(), path) is True
        )
        return matched / len(requested_feature_paths)

    @staticmethod
    def _extract_geo_context(query: dict) -> Optional[dict[str, Any]]:
        location_query = query.get("location", {})
        near_query = location_query.get("$nearSphere")
        if not near_query:
            return None

        geometry = near_query.get("$geometry", {})
        coordinates = geometry.get("coordinates")
        max_distance = near_query.get("$maxDistance")
        if (
            not isinstance(coordinates, list)
            or len(coordinates) != 2
            or coordinates[0] is None
            or coordinates[1] is None
            or not max_distance
        ):
            return None

        return {
            "coordinates": (coordinates[0], coordinates[1]),
            "max_distance": max_distance,
        }

    @staticmethod
    def _distance_score(
        item: PropertyEntity, geo_context: Optional[dict[str, Any]]
    ) -> float:
        if not geo_context:
            return 0.0

        anchor_lng, anchor_lat = geo_context["coordinates"]
        distance_meters = PropertyService._haversine_meters(
            lat1=anchor_lat,
            lng1=anchor_lng,
            lat2=item.latitude,
            lng2=item.longitude,
        )
        max_distance = geo_context["max_distance"]
        if max_distance <= 0:
            return 0.0

        return max(0.0, 1.0 - (distance_meters / max_distance))

    @staticmethod
    def _haversine_meters(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        radius = 6371000
        lat1_rad = math.radians(lat1)
        lat2_rad = math.radians(lat2)
        delta_lat = math.radians(lat2 - lat1)
        delta_lng = math.radians(lng2 - lng1)

        a = (
            math.sin(delta_lat / 2) ** 2
            + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lng / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return radius * c

    @staticmethod
    def _get_nested_value(payload: dict, path: str) -> Any:
        current: Any = payload
        for key in path.split("."):
            if not isinstance(current, dict) or key not in current:
                return None
            current = current[key]
        return current

    @staticmethod
    def _system_actor() -> ActorInfo:
        return ActorInfo(name="system", source="system", role="system")

    @staticmethod
    def _now():
        from datetime import UTC, datetime

        return datetime.now(UTC)

    @staticmethod
    def _merge_synced_property(
        existing: PropertyEntity,
        synced: PropertyEntity,
        actor: ActorInfo,
    ) -> PropertyEntity:
        payload = synced.model_dump(by_alias=True)
        payload.update(
            {
                "_id": existing.id,
                "created_at": existing.created_at,
                "created_by": existing.created_by,
                "updated_at": PropertyService._now(),
                "updated_by": actor,
                "manual_overrides": (
                    existing.manual_overrides.model_dump(exclude_none=True)
                    if existing.manual_overrides
                    else None
                ),
                "is_deleted": existing.is_deleted,
                "deleted_at": existing.deleted_at,
                "deleted_by": (
                    existing.deleted_by.model_dump(exclude_none=True)
                    if existing.deleted_by
                    else None
                ),
            }
        )
        return PropertyEntity(**payload)

    @staticmethod
    def _merge_pet_feature_overrides(
        existing: Optional[PetFeaturesOverride],
        incoming: PetFeaturesOverride,
    ) -> PetFeaturesOverride:
        if existing is None:
            return incoming

        existing_payload = existing.model_dump(exclude_none=True)
        incoming_payload = incoming.model_dump(exclude_none=True)
        merged_payload = PropertyService._deep_merge_dict(
            existing_payload, incoming_payload
        )
        return PetFeaturesOverride(**merged_payload)

    @staticmethod
    def _deep_merge_dict(
        base: dict[str, Any], override: dict[str, Any]
    ) -> dict[str, Any]:
        merged = dict(base)
        for key, value in override.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = PropertyService._deep_merge_dict(merged[key], value)
            else:
                merged[key] = value
        return merged

    async def _create_audit_log(
        self,
        property_id: str,
        action: PropertyAuditAction,
        actor: ActorInfo,
        before: Optional[PropertyEntity],
        after: Optional[PropertyEntity],
        reason: Optional[str] = None,
    ) -> None:
        before_payload = self._serialize_property_for_audit(before)
        after_payload = self._serialize_property_for_audit(after)
        audit_log = PropertyAuditLog(
            property_id=property_id,
            action=action,
            actor=actor,
            reason=reason,
            source=actor.source,
            before=before_payload,
            after=after_payload,
            changes=self._build_changes(before_payload, after_payload),
        )
        await self.audit_repo.create(audit_log)

    @staticmethod
    def _serialize_property_for_audit(
        property_entity: Optional[PropertyEntity],
    ) -> Optional[dict[str, Any]]:
        if property_entity is None:
            return None

        payload = property_entity.model_dump(by_alias=True, exclude_none=True)
        payload.pop("op_segments", None)
        payload.pop("location", None)
        payload.pop("types", None)
        payload.pop("is_open", None)
        return payload

    @staticmethod
    def _to_detail_entity(output: PropertyEntity) -> PropertyDetailEntity:
        return PropertyDetailEntity(
            id=output.id,
            name=output.name,
            address=output.address,
            latitude=output.latitude,
            longitude=output.longitude,
            types=output.types,
            rating=output.ai_analysis.ai_rating,
            tags=output.ai_analysis.highlights,
            regular_opening_hours=output.regular_opening_hours,
            ai_analysis=output.ai_analysis,
            manual_overrides=output.manual_overrides,
            effective_pet_features=output.effective_pet_features,
            created_by=output.created_by,
            updated_by=output.updated_by,
            created_at=output.created_at,
            updated_at=output.updated_at,
            deleted_by=output.deleted_by,
            deleted_at=output.deleted_at,
            is_deleted=output.is_deleted,
        )

    @staticmethod
    def _build_changes(
        before: Optional[dict[str, Any]],
        after: Optional[dict[str, Any]],
        path: str = "",
    ) -> dict[str, dict[str, Any]]:
        changes: dict[str, dict[str, Any]] = {}
        before = before or {}
        after = after or {}
        all_keys = set(before.keys()) | set(after.keys())
        for key in sorted(all_keys):
            current_path = f"{path}.{key}" if path else key
            before_value = before.get(key)
            after_value = after.get(key)

            if isinstance(before_value, dict) and isinstance(after_value, dict):
                changes.update(
                    PropertyService._build_changes(
                        before_value, after_value, current_path
                    )
                )
                continue

            if before_value != after_value:
                changes[current_path] = {
                    "before": before_value,
                    "after": after_value,
                }
        return changes
