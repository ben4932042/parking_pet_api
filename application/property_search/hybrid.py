from application.property_search.rules import normalize_text_for_match
from application.property_search.ranking import score_search_result
from domain.entities.property import PropertyEntity


def rank_keyword_hybrid_results(
    query_text: str,
    lexical_items: list[PropertyEntity],
    vector_items: list[PropertyEntity],
) -> list[PropertyEntity]:
    lexical_ids = {item.id for item in lexical_items}
    vector_ids = {item.id for item in vector_items}
    merged = _merge_unique_properties(lexical_items, vector_items)
    normalized_query = normalize_text_for_match(query_text)

    return sorted(
        merged,
        key=lambda item: _keyword_score(
            item,
            normalized_query=normalized_query,
            from_lexical=item.id in lexical_ids,
            from_vector=item.id in vector_ids,
        ),
        reverse=True,
    )


def rank_combined_search_results(
    *,
    query_text: str,
    keyword_items: list[PropertyEntity],
    semantic_items: list[PropertyEntity],
    semantic_query: dict,
) -> list[PropertyEntity]:
    merged = _merge_unique_properties(keyword_items, semantic_items)
    keyword_ids = {item.id for item in keyword_items}
    semantic_ids = {item.id for item in semantic_items}
    normalized_query = normalize_text_for_match(query_text)

    type_filter = semantic_query.get("primary_type")
    is_open_required = semantic_query.get("is_open") is True
    requested_feature_paths = [
        key
        for key, value in semantic_query.items()
        if key.startswith("effective_pet_features.") and isinstance(value, bool)
    ]
    geo_context = _extract_geo_context(semantic_query)

    return sorted(
        merged,
        key=lambda item: _combined_score(
            item=item,
            normalized_query=normalized_query,
            from_keyword=item.id in keyword_ids,
            from_semantic=item.id in semantic_ids,
            type_filter=type_filter,
            is_open_required=is_open_required,
            requested_feature_paths=requested_feature_paths,
            geo_context=geo_context,
        ),
        reverse=True,
    )


def _keyword_score(
    item: PropertyEntity,
    *,
    normalized_query: str,
    from_lexical: bool,
    from_vector: bool,
) -> float:
    score = 0.0
    normalized_name = normalize_text_for_match(item.name)
    normalized_aliases = [normalize_text_for_match(alias) for alias in item.aliases]

    if normalized_query and normalized_query == normalized_name:
        score += 10.0
    if normalized_query and normalized_query in normalized_aliases:
        score += 9.0
    if normalized_query and normalized_query and normalized_query in normalized_name:
        score += 6.0
    if normalized_query and any(normalized_query in alias for alias in normalized_aliases):
        score += 5.0

    if from_lexical:
        score += 4.0
    if from_vector:
        score += 1.0

    score += (item.rating or 0.0) * 0.1
    return score


def _combined_score(
    item: PropertyEntity,
    *,
    normalized_query: str,
    from_keyword: bool,
    from_semantic: bool,
    type_filter,
    is_open_required: bool,
    requested_feature_paths: list[str],
    geo_context,
) -> float:
    keyword_match_score = _keyword_match_score(item, normalized_query)
    semantic_score = score_search_result(
        item=item,
        type_filter=type_filter,
        is_open_required=is_open_required,
        requested_feature_paths=requested_feature_paths,
        geo_context=geo_context,
    )

    score = 0.0
    if from_keyword:
        score += 1.0
    if from_semantic:
        score += 0.75 + (semantic_score * 2.0)
    else:
        score += (item.rating or 0.0) * 0.05

    score += keyword_match_score
    return score


def _keyword_match_score(item: PropertyEntity, normalized_query: str) -> float:
    score = 0.0
    normalized_name = normalize_text_for_match(item.name)
    normalized_aliases = [normalize_text_for_match(alias) for alias in item.aliases]

    if normalized_query and normalized_query == normalized_name:
        score += 12.0
    if normalized_query and normalized_query in normalized_aliases:
        score += 10.0
    if normalized_query and normalized_query in normalized_name:
        score += 6.0
    if normalized_query and any(normalized_query in alias for alias in normalized_aliases):
        score += 4.5
    return score


def _extract_geo_context(query: dict):
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

    return {"coordinates": (coordinates[0], coordinates[1]), "max_distance": max_distance}


def _merge_unique_properties(
    primary_items: list[PropertyEntity],
    fallback_items: list[PropertyEntity],
) -> list[PropertyEntity]:
    merged: list[PropertyEntity] = []
    seen: set[str] = set()
    for item in [*primary_items, *fallback_items]:
        if item.id in seen:
            continue
        seen.add(item.id)
        merged.append(item)
    return merged
