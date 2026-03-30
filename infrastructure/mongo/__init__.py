from typing import Optional

from motor.motor_asyncio import (
    AsyncIOMotorClient,
    AsyncIOMotorDatabase,
    AsyncIOMotorCollection,
)

from infrastructure.config import settings


class MongoDBClient:
    """
    MongoDB client manager (connection pool).
    Designed to be used as a singleton via DI / bootstrap.
    """

    def __init__(self) -> None:
        self._client: Optional[AsyncIOMotorClient] = None

    def get_client(self) -> AsyncIOMotorClient:
        if self._client is None:
            self._client = AsyncIOMotorClient(settings.mongo.url.get_secret_value())
        return self._client

    def get_database(self) -> AsyncIOMotorDatabase:
        return self.get_client()[settings.mongo.db_name]

    def get_collection(self, name: str) -> AsyncIOMotorCollection:
        return self.get_database()[name]

    async def close(self) -> None:
        if self._client:
            self._client.close()
            self._client = None


if __name__ == "__main__":
    import asyncio

    async def test_connection():
        client = MongoDBClient()
        try:
            db = client.get_database()
            result = await db.command("ping")
            print("MongoDB connected:", result)

        except Exception as e:
            print("MongoDB connection failed:", e)
        finally:
            await client.close()

    asyncio.run(test_connection())
