from fastapi import Depends

from infrastructure.mongo import MongoDBClient
from infrastructure.mongo.place_raw_data import PlaceRawDataRepository
from infrastructure.mongo.property import PropertyRepository
from infrastructure.mongo.user import UserRepository


def get_db_client() -> MongoDBClient:
    return MongoDBClient()

def get_property_repository(client: MongoDBClient = Depends(get_db_client)) -> PropertyRepository:
    return PropertyRepository(
        client=client, collection_name="property_v2"
    )

def get_place_raw_data_repository(client: MongoDBClient = Depends(get_db_client)) -> PlaceRawDataRepository:
    return PlaceRawDataRepository(
        client=client, collection_name="place_raw_data"
    )

def get_user_repository(client: MongoDBClient = Depends(get_db_client)) -> UserRepository:
    return UserRepository(
        client=client, collection_name="user"
    )