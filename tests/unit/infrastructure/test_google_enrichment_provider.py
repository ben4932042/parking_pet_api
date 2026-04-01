from domain.entities.landmark_cache import LandmarkCacheEntity
from infrastructure.google import GoogleEnrichmentProvider


class InMemoryLandmarkCacheRepository:
    def __init__(self):
        self.items = {}

    def get_by_key(self, cache_key: str):
        return self.items.get(cache_key)

    def save(self, entry: LandmarkCacheEntity):
        self.items[entry.cache_key] = entry
        return entry


def _build_provider(cache_repo):
    provider = GoogleEnrichmentProvider.__new__(GoogleEnrichmentProvider)
    provider.landmark_cache_repo = cache_repo
    return provider


def test_geocode_landmark_returns_cached_coordinates_without_calling_google(monkeypatch):
    cache_repo = InMemoryLandmarkCacheRepository()
    cache_repo.save(
        LandmarkCacheEntity(
            cache_key="青埔",
            query_text="青埔",
            display_name="青埔",
            longitude=121.2141,
            latitude=25.0086,
        )
    )
    provider = _build_provider(cache_repo)

    def _fail_if_called(_name: str):
        raise AssertionError("google place api should not be called on cache hit")

    monkeypatch.setattr(
        "infrastructure.google.geocode_landmark_by_name",
        _fail_if_called,
    )

    display_name, coordinates = provider.geocode_landmark("青埔")

    assert display_name == "青埔"
    assert coordinates == (121.2141, 25.0086)


def test_geocode_landmark_saves_cache_after_google_lookup(monkeypatch):
    cache_repo = InMemoryLandmarkCacheRepository()
    provider = _build_provider(cache_repo)

    monkeypatch.setattr(
        "infrastructure.google.geocode_landmark_by_name",
        lambda name: ("青埔", (121.2141, 25.0086)),
    )

    display_name, coordinates = provider.geocode_landmark("  青埔  ")

    assert display_name == "青埔"
    assert coordinates == (121.2141, 25.0086)
    cached = cache_repo.get_by_key("青埔")
    assert cached is not None
    assert cached.query_text == "青埔"
    assert cached.display_name == "青埔"
    assert cached.coordinates == (121.2141, 25.0086)


def test_geocode_landmark_caches_negative_lookup(monkeypatch):
    cache_repo = InMemoryLandmarkCacheRepository()
    provider = _build_provider(cache_repo)

    monkeypatch.setattr(
        "infrastructure.google.geocode_landmark_by_name",
        lambda name: ("查無地標", None),
    )

    display_name, coordinates = provider.geocode_landmark("查無地標")

    assert display_name == "查無地標"
    assert coordinates is None
    cached = cache_repo.get_by_key("查無地標")
    assert cached is not None
    assert cached.display_name == "查無地標"
    assert cached.coordinates is None
