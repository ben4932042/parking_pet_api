from application.property_search.hybrid import (
    rank_combined_search_results,
    should_short_circuit_hybrid_keyword,
)


def test_should_short_circuit_hybrid_keyword_for_exact_lexical_match(
    property_entity_factory,
):
    exact = property_entity_factory(identifier="exact", name="寵物公園")
    ranked = [exact]

    assert (
        should_short_circuit_hybrid_keyword(
            query_text="寵物公園",
            lexical_items=[exact],
            ranked_keyword_items=ranked,
        )
        is True
    )


def test_should_not_short_circuit_hybrid_keyword_for_non_lexical_top_hit(
    property_entity_factory,
):
    lexical = property_entity_factory(identifier="lexical", name="寵物樂園")
    semantic_top = property_entity_factory(identifier="semantic-top", name="寵物公園大草原")

    assert (
        should_short_circuit_hybrid_keyword(
            query_text="寵物公園",
            lexical_items=[lexical],
            ranked_keyword_items=[semantic_top, lexical],
        )
        is False
    )


def test_rank_combined_search_results_orders_keyword_then_semantic_then_vector(
    property_entity_factory,
):
    lexical_keyword = property_entity_factory(
        identifier="lexical-keyword",
        name="寵物公園",
        primary_type="park",
    )
    semantic_match = property_entity_factory(
        identifier="semantic-match",
        name="青埔公七公園",
        primary_type="park",
    )
    vector_only = property_entity_factory(
        identifier="vector-only",
        name="寵物友善大草原",
        primary_type="park",
    )

    ranked = rank_combined_search_results(
        query_text="寵物公園",
        keyword_items=[lexical_keyword, vector_only],
        lexical_keyword_items=[lexical_keyword],
        semantic_items=[semantic_match],
        semantic_query={"primary_type": "park"},
    )

    assert [item.id for item in ranked] == [
        "lexical-keyword",
        "semantic-match",
        "vector-only",
    ]
