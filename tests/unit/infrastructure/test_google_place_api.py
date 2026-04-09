from domain.entities.enrichment import PlaceCandidate
from infrastructure.google.place_api import (
    DETAILS_URL,
    LEGACY_DETAILS_URL,
    geocode_landmark_by_name,
    get_place_details,
    search_nearby_parking,
)


def test_geocode_landmark_by_name_returns_display_name_and_coordinates(monkeypatch):
    def _fake_search(name: str):
        return PlaceCandidate(
            id="place-1",
            origin_search_name=name,
            display_name="青埔",
            place_id="place-1",
            latitude=25.0086,
            longitude=121.2141,
            address="桃園市中壢區",
            primary_type="geocode",
            types=["geocode"],
            user_rating_count=0,
        )

    monkeypatch.setattr(
        "infrastructure.google.place_api.search_basic_information_by_name",
        _fake_search,
    )

    display_name, coordinates = geocode_landmark_by_name("青埔")

    assert display_name == "青埔"
    assert coordinates == (121.2141, 25.0086)


def test_geocode_landmark_by_name_returns_none_when_search_fails(monkeypatch):
    monkeypatch.setattr(
        "infrastructure.google.place_api.search_basic_information_by_name",
        lambda _name: None,
    )

    display_name, coordinates = geocode_landmark_by_name("青埔")

    assert display_name == "青埔"
    assert coordinates is None


def test_search_nearby_parking_returns_normalized_candidates(monkeypatch):
    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "places": [
                    {
                        "id": "parking-1",
                        "displayName": {"text": "停車場 A"},
                        "formattedAddress": "桃園市中壢區",
                        "location": {"latitude": 25.01, "longitude": 121.21},
                        "primaryType": "parking",
                        "types": ["parking", "point_of_interest"],
                    },
                    {
                        "id": None,
                        "displayName": {"text": "broken"},
                        "location": {"latitude": 25.02, "longitude": 121.22},
                    },
                ]
            }

    monkeypatch.setattr(
        "infrastructure.google.place_api.requests.post",
        lambda *args, **kwargs: Response(),
    )

    items = search_nearby_parking(lat=25.01, lng=121.21)

    assert len(items) == 1
    assert items[0].place_id == "parking-1"
    assert items[0].name == "停車場 A"
    assert items[0].latitude == 25.01
    assert items[0].longitude == 121.21


def test_get_place_details_merges_new_and_legacy_reviews_by_author(monkeypatch):
    basic_info = PlaceCandidate(
        id="place-1",
        origin_search_name="測試店家",
        display_name="測試店家",
        place_id="place-1",
        latitude=25.01,
        longitude=121.21,
        address="桃園市中壢區",
        primary_type="cafe",
        types=["cafe"],
        user_rating_count=10,
    )

    class Response:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    def _fake_get(url, **kwargs):
        if url == f"{DETAILS_URL}place-1":
            return Response(
                {
                    "rating": 4.7,
                    "userRatingCount": 123,
                    "priceLevel": "PRICE_LEVEL_MODERATE",
                    "reviews": [
                        {
                            "authorAttribution": {"displayName": "Alice"},
                            "rating": 5,
                            "text": {"text": "new api alice"},
                            "relativePublishTimeDescription": "1 week ago",
                        },
                        {
                            "authorAttribution": {"displayName": "Bob"},
                            "rating": 4,
                            "text": {"text": "new api bob"},
                            "relativePublishTimeDescription": "2 weeks ago",
                        },
                    ],
                }
            )
        if url == LEGACY_DETAILS_URL:
            return Response(
                {
                    "result": {
                        "reviews": [
                            {
                                "author_name": "Alice",
                                "rating": 3,
                                "text": "legacy alice newest",
                                "relative_time_description": "3 days ago",
                            },
                            {
                                "author_name": "Carol",
                                "rating": 5,
                                "text": "legacy carol",
                                "relative_time_description": "4 days ago",
                            },
                        ]
                    }
                }
            )
        raise AssertionError(f"unexpected url: {url}")

    monkeypatch.setattr("infrastructure.google.place_api.requests.get", _fake_get)

    detail = get_place_details(basic_info)

    assert detail is not None
    assert detail.rating == 4.7
    assert detail.user_rating_count == 123
    assert [(review.author, review.text) for review in detail.reviews] == [
        ("Alice", "legacy alice newest"),
        ("Bob", "new api bob"),
        ("Carol", "legacy carol"),
    ]


def test_get_place_details_skips_reviews_with_empty_text(monkeypatch):
    basic_info = PlaceCandidate(
        id="place-1",
        origin_search_name="測試店家",
        display_name="測試店家",
        place_id="place-1",
        latitude=25.01,
        longitude=121.21,
        address="桃園市中壢區",
        primary_type="cafe",
        types=["cafe"],
        user_rating_count=10,
    )

    class Response:
        def __init__(self, payload):
            self._payload = payload

        def raise_for_status(self):
            return None

        def json(self):
            return self._payload

    def _fake_get(url, **kwargs):
        if url == f"{DETAILS_URL}place-1":
            return Response(
                {
                    "rating": 4.7,
                    "userRatingCount": 123,
                    "reviews": [
                        {
                            "authorAttribution": {"displayName": "Alice"},
                            "rating": 5,
                            "text": {"text": "   "},
                            "relativePublishTimeDescription": "1 week ago",
                        },
                        {
                            "authorAttribution": {"displayName": "Bob"},
                            "rating": 4,
                            "text": {"text": "new api bob"},
                            "relativePublishTimeDescription": "2 weeks ago",
                        },
                    ],
                }
            )
        if url == LEGACY_DETAILS_URL:
            return Response(
                {
                    "result": {
                        "reviews": [
                            {
                                "author_name": "Carol",
                                "rating": 5,
                                "text": "",
                                "relative_time_description": "4 days ago",
                            },
                            {
                                "author_name": "Dave",
                                "rating": 5,
                                "text": "legacy dave",
                                "relative_time_description": "1 day ago",
                            },
                        ]
                    }
                }
            )
        raise AssertionError(f"unexpected url: {url}")

    monkeypatch.setattr("infrastructure.google.place_api.requests.get", _fake_get)

    detail = get_place_details(basic_info)

    assert detail is not None
    assert [(review.author, review.text) for review in detail.reviews] == [
        ("Bob", "new api bob"),
        ("Dave", "legacy dave"),
    ]
