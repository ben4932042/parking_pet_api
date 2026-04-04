from infrastructure.mongo import MongoDBClient, get_mongodb_client


class _AsyncClientStub:
    def __init__(self, url: str):
        self.url = url
        self.closed = False

    def __getitem__(self, _name: str):
        return self

    def close(self):
        self.closed = True


def test_get_mongodb_client_returns_shared_manager():
    assert get_mongodb_client() is get_mongodb_client()


def test_mongodb_client_reuses_async_client(monkeypatch):
    async_clients: list[_AsyncClientStub] = []

    def build_async_client(url: str):
        client = _AsyncClientStub(url)
        async_clients.append(client)
        return client

    monkeypatch.setattr("infrastructure.mongo.AsyncIOMotorClient", build_async_client)
    MongoDBClient._async_client = None

    first = MongoDBClient()
    second = MongoDBClient()

    assert first.get_client() is second.get_client()
    assert len(async_clients) == 1


async def test_mongodb_client_close_closes_shared_clients(monkeypatch):
    async_clients: list[_AsyncClientStub] = []

    monkeypatch.setattr(
        "infrastructure.mongo.AsyncIOMotorClient",
        lambda url: async_clients.append(_AsyncClientStub(url)) or async_clients[-1],
    )
    MongoDBClient._async_client = None

    client = MongoDBClient()
    client.get_client()

    await client.close()

    assert async_clients[0].closed is True
    assert MongoDBClient._async_client is None
