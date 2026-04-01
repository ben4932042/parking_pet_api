from application.property_search.hybrid import (
    rank_keyword_hybrid_results,
    should_short_circuit_hybrid_keyword,
)


def test_rank_keyword_hybrid_results_prefers_exact_lexical_match(
    property_entity_factory,
):
    exact = property_entity_factory(identifier="exact", name="青埔公七公園")
    exact.aliases = ["公七公園"]

    vector_only = property_entity_factory(identifier="vector", name="崙坪文化地景園區")
    vector_only.aliases = []

    ranked = rank_keyword_hybrid_results(
        query_text="青埔公七公園",
        lexical_items=[exact],
        vector_items=[vector_only, exact],
    )

    assert [item.id for item in ranked] == ["exact", "vector"]


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


def test_should_not_short_circuit_hybrid_keyword_for_vector_only_top_hit(
    property_entity_factory,
):
    lexical = property_entity_factory(identifier="lexical", name="寵物樂園")
    vector_top = property_entity_factory(identifier="vector-top", name="寵物公園大草原")

    assert (
        should_short_circuit_hybrid_keyword(
            query_text="寵物公園",
            lexical_items=[lexical],
            ranked_keyword_items=[vector_top, lexical],
        )
        is False
    )
