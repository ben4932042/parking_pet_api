from unittest.mock import MagicMock

from infrastructure.mongo.landmark_cache import LandmarkCacheRepository
from infrastructure.mongo.search_plan_cache import SearchPlanCacheRepository


class _ClientStub:
    def __init__(self, collection):
        self.collection = collection
        self.collection_names: list[str] = []

    def get_sync_collection(self, collection_name: str):
        self.collection_names.append(collection_name)
        return self.collection


def test_landmark_cache_repository_uses_injected_sync_client():
    collection = MagicMock()
    client = _ClientStub(collection)

    repo = LandmarkCacheRepository(client=client, collection_name="landmark_cache")

    assert repo.collection is collection
    assert client.collection_names == ["landmark_cache"]
    collection.create_index.assert_called_once_with("cache_key", unique=True)


def test_search_plan_cache_repository_uses_injected_sync_client():
    collection = MagicMock()
    client = _ClientStub(collection)

    repo = SearchPlanCacheRepository(client=client, collection_name="search_plan_cache")

    assert repo.collection is collection
    assert client.collection_names == ["search_plan_cache"]
    collection.create_index.assert_called_once_with("cache_key", unique=True)
