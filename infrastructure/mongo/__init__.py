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

    _async_client: Optional[AsyncIOMotorClient] = None

    def __init__(self) -> None:
        pass

    def get_client(self) -> AsyncIOMotorClient:
        if self.__class__._async_client is None:
            self.__class__._async_client = AsyncIOMotorClient(
                settings.mongo.url.get_secret_value()
            )
        return self.__class__._async_client

    def get_database(self) -> AsyncIOMotorDatabase:
        return self.get_client()[settings.mongo.db_name]

    def get_collection(self, name: str) -> AsyncIOMotorCollection:
        return self.get_database()[name]

    async def close(self) -> None:
        if self.__class__._async_client:
            self.__class__._async_client.close()
            self.__class__._async_client = None


_mongodb_client = MongoDBClient()


def get_mongodb_client() -> MongoDBClient:
    return _mongodb_client


if __name__ == "__main__":
    import asyncio

    async def test_connection():
        client = get_mongodb_client()
        try:
            db = client.get_database()
            result = await db.command("ping")
            print("MongoDB connected:", result)

        except Exception as e:
            print("MongoDB connection failed:", e)
        finally:
            await client.close()

    asyncio.run(test_connection())
