from application.property_search.rules import normalize_text_for_match
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
