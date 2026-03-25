from fastapi import Depends

from infrastructure.mongo import MongoDBClient
from infrastructure.mongo.property import PropertyRepository

def get_db_client() -> MongoDBClient:
    return MongoDBClient()

def get_property_repository(client: MongoDBClient = Depends(get_db_client)) -> PropertyRepository:
    return PropertyRepository(
        client=client, collection_name="property"
    )

