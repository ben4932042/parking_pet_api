from infrastructure.mongo import MongoDBClient, get_mongodb_client


class _AsyncClientStub:
    def __init__(self, url: str):
        self.url = url
        self.closed = False

    def __getitem__(self, _name: str):
        return self

    def close(self):
        self.closed = True


class _SyncClientStub:
    def __init__(self, url: str):
        self.url = url
        self.closed = False

    def __getitem__(self, _name: str):
        return self

    def close(self):
        self.closed = True


def test_get_mongodb_client_returns_shared_manager():
    assert get_mongodb_client() is get_mongodb_client()


def test_mongodb_client_reuses_async_and_sync_clients(monkeypatch):
    async_clients: list[_AsyncClientStub] = []
    sync_clients: list[_SyncClientStub] = []

    def build_async_client(url: str):
        client = _AsyncClientStub(url)
        async_clients.append(client)
        return client

    def build_sync_client(url: str):
        client = _SyncClientStub(url)
        sync_clients.append(client)
        return client

    monkeypatch.setattr("infrastructure.mongo.AsyncIOMotorClient", build_async_client)
    monkeypatch.setattr("infrastructure.mongo.MongoClient", build_sync_client)
    MongoDBClient._async_client = None
    MongoDBClient._sync_client = None

    first = MongoDBClient()
    second = MongoDBClient()

    assert first.get_client() is second.get_client()
    assert first.get_sync_client() is second.get_sync_client()
    assert len(async_clients) == 1
    assert len(sync_clients) == 1


async def test_mongodb_client_close_closes_shared_clients(monkeypatch):
    async_clients: list[_AsyncClientStub] = []
    sync_clients: list[_SyncClientStub] = []

    monkeypatch.setattr(
        "infrastructure.mongo.AsyncIOMotorClient",
        lambda url: async_clients.append(_AsyncClientStub(url)) or async_clients[-1],
    )
    monkeypatch.setattr(
        "infrastructure.mongo.MongoClient",
        lambda url: sync_clients.append(_SyncClientStub(url)) or sync_clients[-1],
    )
    MongoDBClient._async_client = None
    MongoDBClient._sync_client = None

    client = MongoDBClient()
    client.get_client()
    client.get_sync_client()

    await client.close()

    assert async_clients[0].closed is True
    assert sync_clients[0].closed is True
    assert MongoDBClient._async_client is None
    assert MongoDBClient._sync_client is None

