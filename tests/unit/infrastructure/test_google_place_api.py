from domain.entities.enrichment import PlaceCandidate
from infrastructure.google.place_api import geocode_landmark_by_name


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
