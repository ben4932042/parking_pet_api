from application.property_search.rules import normalize_text_for_match
from application.property_search.ranking import score_search_result
from domain.entities.property import PropertyEntity


LEXICAL_PREFIX_BOUNDARY_CHARS = {
    "(",
    ")",
    "[",
    "]",
    "{",
    "}",
    "（",
    "）",
    "-",
    "_",
    " ",
}


def _matches_lexical_lookup_variant(normalized_query: str, candidate: str) -> bool:
    if not candidate.startswith(normalized_query):
        return False

    if len(candidate) == len(normalized_query):
        return True

    next_char = candidate[len(normalized_query)]
    return next_char in LEXICAL_PREFIX_BOUNDARY_CHARS


def is_exact_lexical_match(
    *,
    query_text: str,
    item: PropertyEntity,
) -> bool:
    normalized_query = normalize_text_for_match(query_text)
    if not normalized_query:
        return False

    normalized_name = normalize_text_for_match(item.name)
    normalized_aliases = [normalize_text_for_match(alias) for alias in item.aliases]
    if _matches_lexical_lookup_variant(normalized_query, normalized_name):
        return True
    return any(
        _matches_lexical_lookup_variant(normalized_query, alias)
        for alias in normalized_aliases
    )


def collect_exact_keyword_matches(
    *,
    query_text: str,
    items: list[PropertyEntity],
) -> list[PropertyEntity]:
    return [
        item
        for item in items
        if is_exact_lexical_match(query_text=query_text, item=item)
    ]


def should_short_circuit_hybrid_keyword(
    *,
    query_text: str,
    lexical_items: list[PropertyEntity],
    ranked_keyword_items: list[PropertyEntity],
) -> bool:
    if not lexical_items or not ranked_keyword_items:
        return False

    top_item = ranked_keyword_items[0]
    lexical_ids = {item.id for item in lexical_items}
    if top_item.id not in lexical_ids:
        return False

    return is_exact_lexical_match(query_text=query_text, item=top_item)


def rank_combined_search_results(
    *,
    query_text: str,
    keyword_items: list[PropertyEntity],
    lexical_keyword_items: list[PropertyEntity],
    semantic_items: list[PropertyEntity],
    semantic_query: dict,
) -> list[PropertyEntity]:
    exact_keyword_items = collect_exact_keyword_matches(
        query_text=query_text,
        items=lexical_keyword_items or keyword_items,
    )
    ranked_semantic_items = _rank_semantic_items(semantic_items, semantic_query)
    return _merge_unique_properties(exact_keyword_items, ranked_semantic_items)


def _rank_semantic_items(
    semantic_items: list[PropertyEntity],
    semantic_query: dict,
) -> list[PropertyEntity]:
    type_filter = semantic_query.get("primary_type")
    is_open_required = semantic_query.get("is_open") is True
    requested_feature_paths = [
        key
        for key, value in semantic_query.items()
        if key.startswith("effective_pet_features.") and isinstance(value, bool)
    ]
    geo_context = _extract_geo_context(semantic_query)
    return sorted(
        semantic_items,
        key=lambda item: score_search_result(
            item=item,
            type_filter=type_filter,
            is_open_required=is_open_required,
            requested_feature_paths=requested_feature_paths,
            geo_context=geo_context,
        ),
        reverse=True,
    )


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

    return {
        "coordinates": (coordinates[0], coordinates[1]),
        "max_distance": max_distance,
    }


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
