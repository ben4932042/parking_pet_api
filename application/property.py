import logging
import math
import re
from typing import Any, List, Optional

from application.exceptions import ConflictError, NotFoundError
from application.property_search.hybrid import (
    rank_combined_search_results,
    should_short_circuit_hybrid_keyword,
)
from application.property_search.projection import build_property_alias_fields
from application.property_search.ranking import rank_search_results
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

logger = logging.getLogger(__name__)


PROMPT_INJECTION_ROUTE_REASON = "查詢包含 prompt injection 訊號，改用關鍵字搜尋"
NON_SEARCH_ROUTE_REASON = "查詢內容不像搜尋條件，直接回傳空結果"


class PropertyService:
    def __init__(
        self,
        repo: IPropertyRepository,
        raw_data_repo: IPlaceRawDataRepository,
        audit_repo: IPropertyAuditRepository,
        enrichment_provider: IEnrichmentProvider,
        note_repo: IPropertyNoteRepository | None = None,
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
        radius: Optional[int] = None,
        open_at_minutes: Optional[int] = None,
    ):
        search_plan = self.enrichment_provider.extract_search_plan(q)
        self._apply_radius_override(search_plan, radius)
        logger.debug(f"Search plan: {search_plan}")

        execution_modes = set(search_plan.execution_modes)
        run_keyword = "keyword" in execution_modes or search_plan.used_fallback
        run_semantic = "semantic" in execution_modes and not search_plan.used_fallback

        if execution_modes == {"keyword"}:
            if search_plan.route_reason == PROMPT_INJECTION_ROUTE_REASON:
                logger.warning(
                    "Blocked prompt-injection-like search query",
                    extra={"query_text": q, "route_reason": search_plan.route_reason},
                )
                return [], search_plan
            if search_plan.route_reason == NON_SEARCH_ROUTE_REASON:
                logger.info(
                    "Skipped search for non-search-intent query",
                    extra={"query_text": q, "route_reason": search_plan.route_reason},
                )
                return [], search_plan

        semantic_items: list[PropertyEntity] = []
        keyword_items: list[PropertyEntity] = []
        lexical_keyword_items: list[PropertyEntity] = []
        generate_query: dict[str, Any] = {}
        semantic_ready = False

        if run_semantic:
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
                run_semantic = False
                if not run_keyword:
                    return [], search_plan
            else:
                generate_query = self.enrichment_provider.generate_query(
                    search_plan.filter_condition,
                    user_coords,
                    map_coords,
                )
                semantic_ready = True

        if run_keyword:
            logger.debug(
                "Search using keyword execution path",
                extra={
                    "query_text": q,
                    "fallback_reason": search_plan.fallback_reason,
                    "warnings": search_plan.warnings,
                    "execution_modes": search_plan.execution_modes,
                },
            )
            if run_semantic:
                (
                    keyword_items,
                    lexical_keyword_items,
                ) = await self._search_keyword_hybrid_with_metadata(q)
                if generate_query:
                    keyword_items = self._filter_keyword_items_by_semantic_query(
                        keyword_items,
                        generate_query,
                        open_at_minutes=open_at_minutes,
                    )
                    lexical_keyword_items = (
                        self._filter_keyword_items_by_semantic_query(
                            lexical_keyword_items,
                            generate_query,
                            open_at_minutes=open_at_minutes,
                        )
                    )
                if should_short_circuit_hybrid_keyword(
                    query_text=q,
                    lexical_items=lexical_keyword_items,
                    ranked_keyword_items=keyword_items,
                ):
                    logger.debug(
                        "Short-circuiting hybrid search on high-confidence keyword hit",
                        extra={"query_text": q},
                    )
                    return keyword_items, search_plan
            else:
                keyword_items = await self._search_keyword(q)
                lexical_keyword_items = keyword_items

        if run_semantic and semantic_ready:
            logger.debug(
                "Generated query",
                extra={
                    "query_text": q,
                    "mongo_query": generate_query,
                    "semantic_extraction": search_plan.semantic_extraction,
                    "warnings": search_plan.warnings,
                },
            )
            if keyword_items:
                keyword_items = self._filter_keyword_items_by_semantic_query(
                    keyword_items,
                    generate_query,
                    open_at_minutes=open_at_minutes,
                )
                lexical_keyword_items = self._filter_keyword_items_by_semantic_query(
                    lexical_keyword_items,
                    generate_query,
                    open_at_minutes=open_at_minutes,
                )
            semantic_items = await self.repo.find_by_query(
                generate_query, open_at_minutes=open_at_minutes
            )
            if semantic_items:
                semantic_items = rank_search_results(semantic_items, generate_query)
            else:
                logger.info("Semantic search returned no results.")
                logger.debug(
                    "Semantic query returned no results",
                    extra={
                        "query_text": q,
                        "mongo_query": generate_query,
                    },
                )

        if run_semantic and run_keyword:
            items = rank_combined_search_results(
                query_text=q,
                keyword_items=keyword_items,
                lexical_keyword_items=lexical_keyword_items,
                semantic_items=semantic_items,
                semantic_query=generate_query,
            )
            return items, search_plan
        if run_semantic:
            return semantic_items, search_plan
        return keyword_items, search_plan

    @staticmethod
    def _apply_radius_override(search_plan, radius: Optional[int]) -> None:
        if radius is None or radius <= 0:
            return

        if search_plan.filter_condition.travel_time_limit_min is not None:
            return

        if search_plan.filter_condition.landmark_context:
            return

        if "address" in search_plan.filter_condition.mongo_query:
            return

        search_plan.filter_condition.search_radius_meters = radius
        if search_plan.semantic_extraction:
            search_plan.semantic_extraction["search_radius_meters"] = radius

    def _filter_keyword_items_by_semantic_query(
        self,
        items: list[PropertyEntity],
        semantic_query: dict[str, Any],
        *,
        open_at_minutes: Optional[int] = None,
    ) -> list[PropertyEntity]:
        return [
            item
            for item in items
            if self._matches_semantic_query(
                item,
                semantic_query,
                open_at_minutes=open_at_minutes,
            )
        ]

    def _matches_semantic_query(
        self,
        item: PropertyEntity,
        semantic_query: dict[str, Any],
        *,
        open_at_minutes: Optional[int] = None,
    ) -> bool:
        for key, value in semantic_query.items():
            if key == "primary_type":
                if isinstance(value, dict) and "$in" in value:
                    if item.primary_type not in value["$in"]:
                        return False
                elif item.primary_type != value:
                    return False
            elif key == "rating":
                minimum = value.get("$gte") if isinstance(value, dict) else None
                if minimum is not None and (item.rating or 0.0) < minimum:
                    return False
            elif key == "address":
                pattern = value.get("$regex") if isinstance(value, dict) else None
                if pattern and not re.search(pattern, item.address, re.IGNORECASE):
                    return False
            elif key.startswith("effective_pet_features."):
                if self._get_nested_value(item.model_dump(), key) is not value:
                    return False
            elif key == "location":
                if not self._matches_location_query(item, value):
                    return False
            elif key == "op_segments":
                if not self._matches_op_segments(item, value):
                    return False
            elif key == "is_open" and value is True:
                if not self._matches_open_now(item, open_at_minutes=open_at_minutes):
                    return False
        return True

    @staticmethod
    def _get_nested_value(payload: dict, path: str) -> Any:
        current: Any = payload
        for part in path.split("."):
            if not isinstance(current, dict) or part not in current:
                return None
            current = current[part]
        return current

    @staticmethod
    def _matches_location_query(
        item: PropertyEntity, location_query: dict[str, Any]
    ) -> bool:
        near_query = location_query.get("$nearSphere", {})
        geometry = near_query.get("$geometry", {})
        coordinates = geometry.get("coordinates")
        max_distance = near_query.get("$maxDistance")
        if (
            not isinstance(coordinates, list)
            or len(coordinates) != 2
            or coordinates[0] is None
            or coordinates[1] is None
            or max_distance is None
        ):
            return True

        distance = PropertyService._haversine_meters(
            lat1=coordinates[1],
            lng1=coordinates[0],
            lat2=item.latitude,
            lng2=item.longitude,
        )
        return distance <= max_distance

    @staticmethod
    def _matches_op_segments(
        item: PropertyEntity, op_segment_query: dict[str, Any]
    ) -> bool:
        elem_match = op_segment_query.get("$elemMatch", {})
        max_start = elem_match.get("s", {}).get("$lte")
        min_end = elem_match.get("e", {}).get("$gte")
        for segment in item.op_segments:
            if max_start is not None and segment.s > max_start:
                continue
            if min_end is not None and segment.e < min_end:
                continue
            return True
        return False

    @staticmethod
    def _matches_open_now(
        item: PropertyEntity,
        *,
        open_at_minutes: Optional[int] = None,
    ) -> bool:
        if item.is_open is True and open_at_minutes is None:
            return True
        current_minutes = (
            open_at_minutes
            if open_at_minutes is not None
            else PropertyService._current_taiwan_minutes()
        )
        for segment in item.op_segments:
            if segment.s <= current_minutes <= segment.e:
                return True
        return False

    @staticmethod
    def _current_taiwan_minutes() -> int:
        from datetime import datetime, timedelta, timezone

        tz_taiwan = timezone(timedelta(hours=8))
        now = datetime.now(tz_taiwan)
        day_of_week = (now.weekday() + 1) % 7
        return (day_of_week * 1440) + (now.hour * 60) + now.minute

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

    async def _search_keyword(self, q: str) -> list[PropertyEntity]:
        return await self.repo.get_by_keyword(q)

    async def _search_keyword_hybrid_with_metadata(
        self, q: str
    ) -> tuple[list[PropertyEntity], list[PropertyEntity]]:
        lexical_items = await self.repo.get_by_keyword(q)
        return lexical_items, lexical_items

    async def get_noted_property_ids(
        self, user_id: str, property_ids: list[str]
    ) -> set[str]:
        if self.note_repo is None:
            return set()
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

        final_property = self._apply_search_projection(final_property)
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

    async def update_aliases(
        self,
        property_id: PyObjectId,
        manual_aliases: list[str],
        actor: ActorInfo,
        reason: Optional[str] = None,
    ) -> PropertyDetailEntity:
        existing = await self.repo.get_property_by_id(property_id)
        if existing is None:
            raise NotFoundError("Property not found")

        updated_property = existing.model_copy(
            update={
                "manual_aliases": self._normalize_aliases(manual_aliases),
                "updated_by": actor,
                "updated_at": self._now(),
            }
        )
        updated_property = self._apply_search_projection(updated_property)
        updated_property = PropertyEntity(**updated_property.model_dump(by_alias=True))
        saved_property = await self.repo.save(updated_property)
        await self._create_audit_log(
            property_id=saved_property.id,
            action=PropertyAuditAction.ALIASES_UPDATE,
            actor=actor,
            before=existing,
            after=saved_property,
            reason=reason,
        )
        return self._to_detail_entity(saved_property)

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
            aliases=output.aliases,
            manual_aliases=output.manual_aliases,
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

    def _apply_search_projection(
        self, property_entity: PropertyEntity
    ) -> PropertyEntity:
        return property_entity.model_copy(
            update=build_property_alias_fields(property_entity)
        )

    @staticmethod
    def _normalize_aliases(aliases: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for alias in aliases:
            cleaned = " ".join(alias.split()).strip()
            if not cleaned:
                continue
            lowered = cleaned.casefold()
            if lowered in seen:
                continue
            seen.add(lowered)
            normalized.append(cleaned)
        return normalized

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
