from domain.entities.search_v2 import SearchPlanV2
from domain.entities.property import PropertyFilterCondition
from interface.api.dependencies.property import get_property_service


class CapturePropertyServiceV2:
    def __init__(self):
        self.calls = []

    async def search_by_keyword_v2(self, q, user_coords=None, map_coords=None):
        self.calls.append(
            {
                "q": q,
                "user_coords": user_coords,
                "map_coords": map_coords,
            }
        )
        return [], SearchPlanV2(
            route="semantic",
            filter_condition=PropertyFilterCondition(
                preferences=[{"key": "primary_type_preference", "label": "cafe"}]
            ),
            semantic_extraction={"category": "cafe", "preferences": {"pet_menu": True}},
            warnings=["low_confidence_primary_type"],
            used_fallback=False,
        )


def test_search_v2_route_returns_semantic_payload(client, override_api_dep):
    service = override_api_dep(get_property_service, CapturePropertyServiceV2())

    response = client.get(
        "/api/v2/property",
        params={
            "query": "台北101附近可落地的咖啡廳",
            "map_lat": 25.03,
            "map_lng": 121.56,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["route"] == "semantic"
    assert data["semantic_extraction"]["category"] == "cafe"
    assert data["semantic_extraction"]["preferences"]["pet_menu"] is True
    assert data["warnings"] == ["low_confidence_primary_type"]
    assert data["used_fallback"] is False
    assert service.calls == [
        {
            "q": "台北101附近可落地的咖啡廳",
            "user_coords": None,
            "map_coords": (121.56, 25.03),
        }
    ]
