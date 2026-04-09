import logging
import math
import re
from dataclasses import dataclass
from typing import Any, List, Optional

from application.dto.property import (
    AIAnalysisDto,
    ActorDto,
    OpeningPeriodDto,
    PetEnvironmentDto,
    PetEnvironmentOverrideDto,
    PetFeaturesDto,
    PetFeaturesOverrideDto,
    PetRulesDto,
    PetRulesOverrideDto,
    PetServiceDto,
    PetServiceOverrideDto,
    PropertyAliasesDto,
    PropertyAuditLogDto,
    PropertyDetailDto,
    PropertyMapBboxDto,
    PropertyMapResultDto,
    PropertyCreateResultDto,
    PropertyManualOverridesDto,
    PropertyMutationDto,
    PropertyMutationResultDto,
    PropertyOverviewDto,
    PropertyPetFeaturesDto,
    PropertySearchResultDto,
    ReviewDto,
    TimePointDto,
)
from application.exceptions import ConflictError, NotFoundError
from application.property_search.constants import (
    NON_SEARCH_ROUTE_REASON,
    PROMPT_INJECTION_ROUTE_REASON,
)
from application.property_search.hybrid import (
    collect_exact_keyword_matches,
    rank_combined_search_results,
)
from application.property_search.projection import build_property_alias_fields
from application.property_search.ranking import rank_search_results
from domain.entities.audit import ActorInfo, PropertyAuditAction, PropertyAuditLog
from domain.entities import PyObjectId
from domain.entities.enrichment import AnalysisSource, Review
from domain.entities.parking import ParkingEntity
from domain.entities.property import (
    PetEnvironmentOverride,
    PetFeaturesOverride,
    PetRulesOverride,
    PetServiceOverride,
    PropertyEntity,
    PropertyManualOverrides,
)
from domain.entities.property_category import PropertyCategoryKey
from domain.entities.property_category import get_primary_types_by_category_key
from domain.entities.user import UserEntity
from domain.repositories.place_raw_data import IPlaceRawDataRepository
from domain.repositories.parking import IParkingRepository
from domain.repositories.property_audit import IPropertyAuditRepository
from domain.repositories.property import IPropertyRepository
from domain.services.property_enrichment import IEnrichmentProvider

logger = logging.getLogger(__name__)


HYBRID_KEYWORD_NEAREST_RADIUS_METERS = 100000


@dataclass
class PropertyUpsertResult:
    property: PropertyEntity
    changed: bool
    existing_before: bool
    outcome: str


@dataclass
class PropertyCreateResultEnvelope:
    property: PropertyEntity
    result: PropertyCreateResultDto


class PropertyService:
    PERSISTED_PROPERTY_FIELDS = {
        "_id",
        "name",
        "place_id",
        "aliases",
        "manual_aliases",
        "latitude",
        "longitude",
        "regular_opening_hours",
        "address",
        "ai_analysis",
        "manual_overrides",
        "effective_pet_features",
        "created_by",
        "updated_by",
        "deleted_by",
        "deleted_at",
        "is_deleted",
        "created_at",
        "updated_at",
        "op_segments",
        "location",
        "primary_type",
        "rating",
        "category",
    }

    def __init__(
        self,
        repo: IPropertyRepository,
        raw_data_repo: IPlaceRawDataRepository,
        audit_repo: IPropertyAuditRepository,
        enrichment_provider: IEnrichmentProvider,
        parking_repo: IParkingRepository | None = None,
    ):
        self.repo = repo
        self.raw_data_repo = raw_data_repo
        self.audit_repo = audit_repo
        self.enrichment_provider = enrichment_provider
        self.parking_repo = parking_repo

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

    async def get_nearby_overviews(
        self,
        lat: float,
        lng: float,
        radius: int,
        types: List[str],
        page: int,
        size: int,
        current_user: UserEntity | None = None,
    ) -> tuple[list[PropertyOverviewDto], int]:
        items, total = await self.search_nearby(lat, lng, radius, types, page, size)
        return self._to_overview_dtos(items, current_user=current_user), total

    async def get_map_overviews(
        self,
        min_lat: float,
        max_lat: float,
        min_lng: float,
        max_lng: float,
        types: list[str],
        query: str | None,
        limit: int,
        category: PropertyCategoryKey | None = None,
        current_user: UserEntity | None = None,
    ) -> PropertyMapResultDto:
        items, total = await self.repo.get_in_bbox(
            min_lat=min_lat,
            max_lat=max_lat,
            min_lng=min_lng,
            max_lng=max_lng,
            types=types,
            query=query,
            limit=limit,
        )
        overview_items = self._to_overview_dtos(items, current_user=current_user)
        returned_count = len(overview_items)
        truncated = total > returned_count
        return PropertyMapResultDto(
            bbox=PropertyMapBboxDto(
                min_lat=min_lat,
                max_lat=max_lat,
                min_lng=min_lng,
                max_lng=max_lng,
            ),
            query=query,
            category=category.value if category is not None else None,
            items=overview_items,
            total_in_bbox=total,
            returned_count=returned_count,
            truncated=truncated,
            suggest_clustering=truncated,
        )

    async def search_properties(
        self,
        q: str,
        category: Optional[PropertyCategoryKey] = None,
        user_coords: Optional[tuple[float, float]] = None,
        map_coords: Optional[tuple[float, float]] = None,
        radius: Optional[int] = None,
        open_at_minutes: Optional[int] = None,
        current_user: UserEntity | None = None,
    ) -> PropertySearchResultDto:
        items, plan = await self.search_by_keyword(
            q=q,
            category=category,
            user_coords=user_coords,
            map_coords=map_coords,
            radius=radius,
            open_at_minutes=open_at_minutes,
        )
        overview_items = self._to_overview_dtos(items, current_user=current_user)
        return PropertySearchResultDto(
            status="success",
            user_query=q,
            response_type=self._response_type_from_plan(
                plan.execution_modes,
                plan.used_fallback,
            ),
            preferences=plan.filter_condition.preferences,
            categories=self._collect_result_categories(overview_items),
            results=overview_items,
        )

    async def search_by_keyword(
        self,
        q: str,
        category: Optional[PropertyCategoryKey] = None,
        user_coords: Optional[tuple[float, float]] = None,
        map_coords: Optional[tuple[float, float]] = None,
        radius: Optional[int] = None,
        open_at_minutes: Optional[int] = None,
    ):
        search_plan = await self.enrichment_provider.extract_search_plan(q)
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
                generate_query = await self.enrichment_provider.generate_query(
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
                keyword_items = collect_exact_keyword_matches(
                    query_text=q,
                    items=keyword_items,
                )
                lexical_keyword_items = collect_exact_keyword_matches(
                    query_text=q,
                    items=lexical_keyword_items,
                )
                if self._should_use_nearest_keyword_hybrid_result(
                    search_plan, map_coords=map_coords
                ):
                    keyword_items = self._nearest_keyword_items(
                        keyword_items,
                        map_coords=map_coords,
                        radius_meters=HYBRID_KEYWORD_NEAREST_RADIUS_METERS,
                    )
                    lexical_keyword_items = self._nearest_keyword_items(
                        lexical_keyword_items,
                        map_coords=map_coords,
                        radius_meters=HYBRID_KEYWORD_NEAREST_RADIUS_METERS,
                    )
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
            return self._filter_items_by_category(items, category), search_plan
        if run_semantic:
            return self._filter_items_by_category(semantic_items, category), search_plan
        return self._filter_items_by_category(keyword_items, category), search_plan

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

    @staticmethod
    def _filter_items_by_category(
        items: list[PropertyEntity],
        category: Optional[PropertyCategoryKey],
    ) -> list[PropertyEntity]:
        if category is None:
            return items
        allowed_types = set(get_primary_types_by_category_key(category))
        if not allowed_types:
            return []
        return [item for item in items if item.primary_type in allowed_types]

    @staticmethod
    def _should_use_nearest_keyword_hybrid_result(
        search_plan,
        *,
        map_coords: Optional[tuple[float, float]] = None,
    ) -> bool:
        if map_coords is None:
            return False

        condition = search_plan.filter_condition
        if condition.landmark_context:
            return False
        if condition.travel_time_limit_min is not None:
            return False
        if "address" in condition.mongo_query:
            return False
        return True

    @classmethod
    def _nearest_keyword_items(
        cls,
        items: list[PropertyEntity],
        *,
        map_coords: Optional[tuple[float, float]],
        radius_meters: int,
    ) -> list[PropertyEntity]:
        if map_coords is None:
            return items

        candidates: list[tuple[float, PropertyEntity]] = []
        map_lng, map_lat = map_coords
        for item in items:
            if item.latitude is None or item.longitude is None:
                continue
            distance = cls._haversine_meters(
                map_lat,
                map_lng,
                item.latitude,
                item.longitude,
            )
            if distance <= radius_meters:
                candidates.append((distance, item))

        if not candidates:
            return []

        candidates.sort(key=lambda candidate: candidate[0])
        return [candidates[0][1]]

    @staticmethod
    def _merge_unique_items(
        priority_items: list[PropertyEntity],
        fallback_items: list[PropertyEntity],
    ) -> list[PropertyEntity]:
        merged: list[PropertyEntity] = []
        seen: set[str] = set()
        for item in [*priority_items, *fallback_items]:
            item_id = str(item.id)
            if item_id in seen:
                continue
            seen.add(item_id)
            merged.append(item)
        return merged

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

    async def get_overviews_by_ids(
        self,
        property_ids: list[str],
        current_user: UserEntity | None = None,
        note_first: bool = False,
    ) -> list[PropertyOverviewDto]:
        items = await self.repo.get_properties_by_ids(property_ids)
        return self._to_overview_dtos(
            items,
            current_user=current_user,
            note_first=note_first,
        )

    async def _search_keyword(self, q: str) -> list[PropertyEntity]:
        return await self.repo.get_by_keyword(q)

    async def _search_keyword_hybrid_with_metadata(
        self, q: str
    ) -> tuple[list[PropertyEntity], list[PropertyEntity]]:
        lexical_items = await self.repo.get_by_keyword(q)
        return lexical_items, lexical_items

    async def get_details(self, property_id: PyObjectId) -> Optional[PropertyDetailDto]:
        output: PropertyEntity = await self.repo.get_property_by_id(property_id)
        if output is None:
            return None
        raw_source = await self.raw_data_repo.get_by_place_id(output.place_id)
        return self._to_detail_dto(output, raw_source=raw_source)

    async def create_property(self, name: str, actor: Optional[ActorInfo] = None):
        return (await self.create_property_result(name=name, actor=actor)).property

    async def create_property_result(
        self, name: str, actor: Optional[ActorInfo] = None
    ) -> PropertyCreateResultEnvelope:
        actor = actor or self._system_actor()
        source_data = self.enrichment_provider.create_property_by_name(name)
        if source_data is None:
            raise ValueError("Failed to resolve property from the provided keyword.")
        result = await self._upsert_property_from_source(
            source_data,
            actor=actor,
            allow_create=True,
            update_outcome="synced",
        )
        await self._sync_nearby_parking_for_property(result.property)
        return PropertyCreateResultEnvelope(
            property=result.property,
            result=PropertyCreateResultDto(
                property_id=result.property.id,
                place_id=result.property.place_id,
                outcome=result.outcome,
                changed=result.changed,
                existing_before=result.existing_before,
            ),
        )

    async def renew_property(
        self,
        property_id: PyObjectId,
        mode: str,
        force: bool = False,
        actor: Optional[ActorInfo] = None,
        reason: Optional[str] = None,
    ) -> tuple[PropertyEntity, bool]:
        actor = actor or self._system_actor()
        existing = await self.repo.get_property_by_id(property_id, include_deleted=True)
        if existing is None:
            raise NotFoundError("Property not found")
        if existing.is_deleted:
            raise ConflictError("Property is soft-deleted. Restore it before renewing.")

        previous_source_data = await self.raw_data_repo.get_by_place_id(
            existing.place_id
        )

        if mode == "details":
            if previous_source_data is None:
                raise ConflictError(
                    "Raw source not found for this property. Renew from basic mode first."
                )
            source_data = self.enrichment_provider.renew_property_from_details(
                previous_source_data
            )
        elif mode == "basic":
            source_data = self.enrichment_provider.renew_property_from_basic(
                existing.place_id
            )
            if source_data is None:
                raise ValueError("Failed to renew property from the upstream provider.")
        else:
            raise ValueError("Unsupported renew mode.")

        if source_data is None:
            raise ValueError("Failed to renew property from the upstream provider.")

        result = await self._upsert_property_from_source(
            source_data,
            actor=actor,
            reason=reason,
            allow_create=False,
            update_outcome="renewed",
            force_ai_refresh=force,
        )
        if mode == "basic":
            await self._sync_nearby_parking_for_property(result.property)
        return result.property, result.changed

    async def renew_property_result(
        self,
        property_id: PyObjectId,
        mode: str,
        force: bool = False,
        actor: Optional[ActorInfo] = None,
        reason: Optional[str] = None,
    ) -> PropertyMutationDto:
        return (
            await self.renew_property_result_with_outcome(
                property_id=property_id,
                mode=mode,
                force=force,
                actor=actor,
                reason=reason,
            )
        ).mutation

    async def renew_property_result_with_outcome(
        self,
        property_id: PyObjectId,
        mode: str,
        force: bool = False,
        actor: Optional[ActorInfo] = None,
        reason: Optional[str] = None,
    ) -> PropertyMutationResultDto:
        renewed_property, changed = await self.renew_property(
            property_id=property_id,
            mode=mode,
            force=force,
            actor=actor,
            reason=reason,
        )
        mutation = self._to_mutation_dto(
            renewed_property,
            status="renewed" if changed else "unchanged",
        )
        return PropertyMutationResultDto(
            mutation=mutation,
            place_id=renewed_property.place_id,
            operation="renew",
            outcome="renewed" if changed else "unchanged",
            changed=changed,
            existing_before=True,
            reason=reason,
            mode=mode,
        )

    async def _upsert_property_from_source(
        self,
        source_data: AnalysisSource,
        *,
        actor: ActorInfo,
        reason: Optional[str] = None,
        allow_create: bool,
        update_outcome: str,
        force_ai_refresh: bool = False,
    ) -> "PropertyUpsertResult":
        previous_source_data = await self.raw_data_repo.get_by_place_id(
            source_data.place_id
        )
        merged_source_data = self._merge_raw_source_data(
            previous=previous_source_data,
            latest=source_data,
        )
        reviews_changed = self._reviews_changed(
            previous=previous_source_data,
            merged=merged_source_data,
        )
        user_rating_count_changed = self._user_rating_count_changed(
            previous=previous_source_data,
            latest=source_data,
        )
        logger.info(
            "Resolved property source update state",
            extra={
                "place_id": source_data.place_id,
                "previous_review_count": (
                    len(previous_source_data.reviews)
                    if previous_source_data is not None
                    else 0
                ),
                "latest_review_count": len(source_data.reviews),
                "merged_review_count": len(merged_source_data.reviews),
                "previous_user_rating_count": (
                    previous_source_data.user_rating_count
                    if previous_source_data is not None
                    else None
                ),
                "latest_user_rating_count": source_data.user_rating_count,
                "reviews_changed": reviews_changed,
                "user_rating_count_changed": user_rating_count_changed,
                "force_ai_refresh": force_ai_refresh,
            },
        )
        await self.raw_data_repo.save(merged_source_data)
        existing = await self.repo.get_property_by_place_id(
            source_data.place_id, include_deleted=True
        )
        if existing is None and not allow_create:
            raise NotFoundError("Property not found")
        if existing and existing.is_deleted:
            raise ConflictError(
                "Property is soft-deleted. Restore it before syncing again."
            )

        if existing:
            if force_ai_refresh or user_rating_count_changed or reviews_changed:
                logger.info(
                    "Property sync requires AI regeneration",
                    extra={
                        "property_id": existing.id,
                        "place_id": source_data.place_id,
                        "reviews_changed": reviews_changed,
                        "user_rating_count_changed": user_rating_count_changed,
                        "force_ai_refresh": force_ai_refresh,
                        "merged_review_count": len(merged_source_data.reviews),
                    },
                )
                ai_result = self.enrichment_provider.generate_ai_analysis(
                    merged_source_data
                )
                if ai_result is None:
                    raise ValueError(
                        "Failed to generate AI analysis for the resolved property."
                    )
                final_property = self._merge_synced_property(existing, ai_result, actor)
                action = PropertyAuditAction.SYNC
                before = existing
            else:
                logger.info(
                    "Property sync skipped because upstream review signals are unchanged",
                    extra={
                        "property_id": existing.id,
                        "place_id": source_data.place_id,
                        "previous_review_count": (
                            len(previous_source_data.reviews)
                            if previous_source_data is not None
                            else 0
                        ),
                        "merged_review_count": len(merged_source_data.reviews),
                        "previous_user_rating_count": (
                            previous_source_data.user_rating_count
                            if previous_source_data is not None
                            else None
                        ),
                        "latest_user_rating_count": source_data.user_rating_count,
                    },
                )
                return PropertyUpsertResult(
                    property=existing,
                    changed=False,
                    existing_before=True,
                    outcome="unchanged",
                )
        else:
            ai_result = self.enrichment_provider.generate_ai_analysis(
                merged_source_data
            )
            if ai_result is None:
                raise ValueError(
                    "Failed to generate AI analysis for the resolved property."
                )
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
            reason=reason,
        )
        logging.info(
            "Property upsert completed successfully",
            extra={
                "place_id": saved_property.place_id,
                "property_id": saved_property.id,
            },
        )
        return PropertyUpsertResult(
            property=saved_property,
            changed=True,
            existing_before=existing is not None,
            outcome=update_outcome if existing else "created",
        )

    async def _sync_nearby_parking_for_property(self, property_entity: PropertyEntity):
        if self.parking_repo is None:
            logger.info(
                "Skipping nearby parking sync because parking repository is unavailable",
                extra={
                    "property_id": property_entity.id,
                    "place_id": property_entity.place_id,
                },
            )
            return

        try:
            logger.info(
                "Starting nearby parking sync for property",
                extra={
                    "property_id": property_entity.id,
                    "place_id": property_entity.place_id,
                    "lat": property_entity.latitude,
                    "lng": property_entity.longitude,
                },
            )
            candidates = self.enrichment_provider.search_nearby_parking(
                lat=property_entity.latitude,
                lng=property_entity.longitude,
            )
            saved_count = 0
            for candidate in candidates:
                await self.parking_repo.save(ParkingEntity.from_candidate(candidate))
                saved_count += 1
            logger.info(
                "Nearby parking sync completed for property",
                extra={
                    "property_id": property_entity.id,
                    "place_id": property_entity.place_id,
                    "candidate_count": len(candidates),
                    "saved_count": saved_count,
                },
            )
        except Exception:
            logger.exception(
                "Failed to sync nearby parking for property",
                extra={
                    "property_id": property_entity.id,
                    "place_id": property_entity.place_id,
                },
            )

    async def update_aliases(
        self,
        property_id: PyObjectId,
        manual_aliases: list[str],
        actor: ActorInfo,
        reason: Optional[str] = None,
    ) -> PropertyAliasesDto:
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
        return PropertyAliasesDto(
            property_id=saved_property.id,
            aliases=saved_property.aliases,
            manual_aliases=saved_property.manual_aliases,
            updated_by=self._to_actor_dto(saved_property.updated_by),
            updated_at=saved_property.updated_at,
            reason=reason,
        )

    async def update_pet_features(
        self,
        property_id: PyObjectId,
        pet_rules: Optional[PetRulesOverride],
        pet_environment: Optional[PetEnvironmentOverride],
        pet_service: Optional[PetServiceOverride],
        actor: ActorInfo,
        reason: Optional[str] = None,
    ) -> PropertyPetFeaturesDto:
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
        return PropertyPetFeaturesDto(
            property_id=saved_property.id,
            inferred_pet_features=self._to_pet_features_dto(
                saved_property.ai_analysis.pet_features
            ),
            manual_pet_features=self._to_pet_features_override_dto(
                saved_property.manual_overrides.pet_features
                if saved_property.manual_overrides
                else None
            ),
            effective_pet_features=self._to_pet_features_dto(
                saved_property.effective_pet_features
            ),
            updated_by=self._to_actor_dto(saved_property.updated_by),
            updated_at=saved_property.updated_at,
            reason=(
                saved_property.manual_overrides.reason
                if saved_property.manual_overrides
                else None
            ),
        )

    async def soft_delete_property(
        self,
        property_id: PyObjectId,
        actor: ActorInfo,
        reason: Optional[str] = None,
    ) -> PropertyMutationDto:
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
        return self._to_mutation_dto(saved_property, status="deleted")

    async def restore_property(
        self,
        property_id: PyObjectId,
        actor: ActorInfo,
        reason: Optional[str] = None,
    ) -> PropertyMutationDto:
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
        return self._to_mutation_dto(saved_property, status="restored")

    async def get_audit_logs(
        self, property_id: PyObjectId, limit: int = 50
    ) -> list[PropertyAuditLogDto]:
        existing = await self.repo.get_property_by_id(property_id, include_deleted=True)
        if existing is None:
            raise NotFoundError("Property not found")
        logs = await self.audit_repo.list_by_property_id(
            property_id=str(property_id), limit=limit
        )
        return [self._to_audit_log_dto(log) for log in logs]

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
        return PropertyEntity(
            **{
                key: value
                for key, value in payload.items()
                if key in PropertyService.PERSISTED_PROPERTY_FIELDS
            }
        )

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
    def _response_type_from_plan(
        execution_modes: list[str],
        used_fallback: bool,
    ) -> str:
        modes = set(execution_modes)
        if modes == {"semantic", "keyword"}:
            return "hybrid_search"
        if modes == {"keyword"}:
            return "keyword_search"
        if used_fallback:
            return "keyword_search"
        return "semantic_search"

    @staticmethod
    def _collect_result_categories(results: list[PropertyOverviewDto]) -> list[str]:
        categories: list[str] = []
        for item in results:
            if item.category is None or item.category in categories:
                continue
            categories.append(item.category)
        return categories

    @staticmethod
    def _noted_property_ids(current_user: UserEntity | None) -> set[str]:
        if current_user is None:
            return set()
        return {note.property_id for note in current_user.property_notes}

    @staticmethod
    def _favorite_property_ids(current_user: UserEntity | None) -> set[str]:
        if current_user is None:
            return set()
        return set(current_user.favorite_property_ids)

    def _to_overview_dtos(
        self,
        items: list[PropertyEntity],
        current_user: UserEntity | None = None,
        note_first: bool = False,
    ) -> list[PropertyOverviewDto]:
        noted_property_ids = self._noted_property_ids(current_user)
        favorite_property_ids = self._favorite_property_ids(current_user)
        overview_items = [
            PropertyOverviewDto(
                id=item.id,
                name=item.name,
                address=item.address,
                latitude=item.latitude,
                longitude=item.longitude,
                category=item.category,
                types=item.types,
                rating=item.rating or 0.0,
                is_open=item.is_open,
                has_note=item.id in noted_property_ids,
                is_favorite=item.id in favorite_property_ids,
            )
            for item in items
        ]
        if note_first:
            overview_items.sort(key=lambda item: not item.has_note)
        return overview_items

    @staticmethod
    def _to_actor_dto(actor: ActorInfo | None) -> ActorDto | None:
        if actor is None:
            return None
        return ActorDto(
            user_id=actor.user_id,
            name=actor.name,
            role=actor.role,
            source=actor.source,
        )

    @staticmethod
    def _to_time_point_dto(time_point) -> TimePointDto:
        return TimePointDto(
            day=time_point.day,
            hour=time_point.hour,
            minute=time_point.minute,
        )

    @classmethod
    def _to_opening_period_dto(cls, period) -> OpeningPeriodDto:
        return OpeningPeriodDto(
            open=cls._to_time_point_dto(period.open),
            close=cls._to_time_point_dto(period.close) if period.close else None,
        )

    @staticmethod
    def _to_pet_features_dto(features) -> PetFeaturesDto | None:
        if features is None:
            return None
        return PetFeaturesDto(
            rules=PetRulesDto(
                leash_required=features.rules.leash_required,
                stroller_required=features.rules.stroller_required,
                allow_on_floor=features.rules.allow_on_floor,
            ),
            environment=PetEnvironmentDto(
                stairs=features.environment.stairs,
                outdoor_seating=features.environment.outdoor_seating,
                spacious=features.environment.spacious,
                indoor_ac=features.environment.indoor_ac,
                off_leash_possible=features.environment.off_leash_possible,
                pet_friendly_floor=features.environment.pet_friendly_floor,
                has_shop_pet=features.environment.has_shop_pet,
            ),
            services=PetServiceDto(
                pet_menu=features.services.pet_menu,
                free_water=features.services.free_water,
                free_treats=features.services.free_treats,
                pet_seating=features.services.pet_seating,
            ),
        )

    @staticmethod
    def _to_pet_features_override_dto(
        features: PetFeaturesOverride | None,
    ) -> PetFeaturesOverrideDto | None:
        if features is None:
            return None
        return PetFeaturesOverrideDto(
            rules=(
                PetRulesOverrideDto(
                    leash_required=features.rules.leash_required,
                    stroller_required=features.rules.stroller_required,
                    allow_on_floor=features.rules.allow_on_floor,
                )
                if features.rules
                else None
            ),
            environment=(
                PetEnvironmentOverrideDto(
                    stairs=features.environment.stairs,
                    outdoor_seating=features.environment.outdoor_seating,
                    spacious=features.environment.spacious,
                    indoor_ac=features.environment.indoor_ac,
                    off_leash_possible=features.environment.off_leash_possible,
                    pet_friendly_floor=features.environment.pet_friendly_floor,
                    has_shop_pet=features.environment.has_shop_pet,
                )
                if features.environment
                else None
            ),
            services=(
                PetServiceOverrideDto(
                    pet_menu=features.services.pet_menu,
                    free_water=features.services.free_water,
                    free_treats=features.services.free_treats,
                    pet_seating=features.services.pet_seating,
                )
                if features.services
                else None
            ),
        )

    @classmethod
    def _to_ai_analysis_dto(cls, analysis) -> AIAnalysisDto:
        return AIAnalysisDto(
            venue_type=analysis.venue_type,
            ai_summary=analysis.ai_summary,
            pet_features=cls._to_pet_features_dto(analysis.pet_features),
            highlights=analysis.highlights,
            warnings=analysis.warnings,
            rating=analysis.ai_rating,
        )

    @classmethod
    def _to_manual_overrides_dto(
        cls, overrides: PropertyManualOverrides | None
    ) -> PropertyManualOverridesDto | None:
        if overrides is None:
            return None
        return PropertyManualOverridesDto(
            pet_features=cls._to_pet_features_override_dto(overrides.pet_features),
            updated_by=cls._to_actor_dto(overrides.updated_by),
            updated_at=overrides.updated_at,
            reason=overrides.reason,
        )

    @classmethod
    def _to_review_dto(cls, review: Review) -> ReviewDto:
        return ReviewDto(
            author=review.author,
            rating=review.rating,
            text=review.text,
            time=review.time,
        )

    @classmethod
    def _to_detail_dto(
        cls,
        output: PropertyEntity,
        *,
        raw_source: AnalysisSource | None = None,
    ) -> PropertyDetailDto:
        return PropertyDetailDto(
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
            regular_opening_hours=(
                [
                    cls._to_opening_period_dto(period)
                    for period in output.regular_opening_hours
                ]
                if output.regular_opening_hours
                else None
            ),
            ai_analysis=cls._to_ai_analysis_dto(output.ai_analysis),
            manual_overrides=cls._to_manual_overrides_dto(output.manual_overrides),
            effective_pet_features=cls._to_pet_features_dto(
                output.effective_pet_features
            ),
            source_user_rating_count=(
                raw_source.user_rating_count if raw_source is not None else None
            ),
            source_reviews=(
                [cls._to_review_dto(review) for review in raw_source.reviews]
                if raw_source is not None
                else []
            ),
            created_by=cls._to_actor_dto(output.created_by),
            updated_by=cls._to_actor_dto(output.updated_by),
            created_at=output.created_at,
            updated_at=output.updated_at,
            deleted_by=cls._to_actor_dto(output.deleted_by),
            deleted_at=output.deleted_at,
            is_deleted=output.is_deleted,
        )

    def _to_mutation_dto(
        self, property_entity: PropertyEntity, status: str
    ) -> PropertyMutationDto:
        return PropertyMutationDto(
            property_id=property_entity.id,
            status=status,
            is_deleted=property_entity.is_deleted,
            updated_by=self._to_actor_dto(property_entity.updated_by),
            updated_at=property_entity.updated_at,
            deleted_by=self._to_actor_dto(property_entity.deleted_by),
            deleted_at=property_entity.deleted_at,
        )

    @classmethod
    def _to_audit_log_dto(cls, log: PropertyAuditLog) -> PropertyAuditLogDto:
        return PropertyAuditLogDto(
            property_id=log.property_id,
            action=log.action.value
            if hasattr(log.action, "value")
            else str(log.action),
            actor=cls._to_actor_dto(log.actor),
            reason=log.reason,
            source=log.source,
            changes=log.changes,
            before=log.before,
            after=log.after,
            created_at=log.created_at,
        )

    def _apply_search_projection(
        self, property_entity: PropertyEntity
    ) -> PropertyEntity:
        return property_entity.model_copy(
            update=build_property_alias_fields(property_entity)
        )

    @staticmethod
    def _resolve_renew_search_name(
        *,
        existing: PropertyEntity,
        previous_source: AnalysisSource | None,
    ) -> str:
        if previous_source is not None and previous_source.origin_search_name:
            return previous_source.origin_search_name
        return existing.name

    @staticmethod
    def _normalize_review_author(author: str | None) -> str | None:
        if author is None:
            return None
        normalized = author.strip()
        return normalized or None

    @classmethod
    def _merge_reviews_by_author(
        cls,
        previous_reviews: list[Review],
        latest_reviews: list[Review],
    ) -> list[Review]:
        merged_reviews: list[Review] = []
        author_to_index: dict[str, int] = {}

        for review in previous_reviews:
            author = cls._normalize_review_author(review.author)
            if author is None:
                continue
            normalized_review = review.model_copy(update={"author": author})
            author_to_index[author] = len(merged_reviews)
            merged_reviews.append(normalized_review)

        for review in latest_reviews:
            author = cls._normalize_review_author(review.author)
            if author is None:
                continue
            normalized_review = review.model_copy(update={"author": author})
            existing_index = author_to_index.get(author)
            if existing_index is None:
                author_to_index[author] = len(merged_reviews)
                merged_reviews.append(normalized_review)
            else:
                merged_reviews[existing_index] = normalized_review

        return merged_reviews

    @classmethod
    def _merge_raw_source_data(
        cls,
        *,
        previous: AnalysisSource | None,
        latest: AnalysisSource,
    ) -> AnalysisSource:
        if previous is None:
            return latest

        return latest.model_copy(
            update={
                "reviews": cls._merge_reviews_by_author(
                    previous.reviews,
                    latest.reviews,
                )
            }
        )

    @staticmethod
    def _reviews_changed(
        *,
        previous: AnalysisSource | None,
        merged: AnalysisSource,
    ) -> bool:
        if previous is None:
            return bool(merged.reviews)
        return previous.reviews != merged.reviews

    @staticmethod
    def _user_rating_count_changed(
        *,
        previous: AnalysisSource | None,
        latest: AnalysisSource,
    ) -> bool:
        if previous is None:
            return False
        return previous.user_rating_count != latest.user_rating_count

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
