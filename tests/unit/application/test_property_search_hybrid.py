from application.property_search.hybrid import rank_keyword_hybrid_results


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
