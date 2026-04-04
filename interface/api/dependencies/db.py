from fastapi import Depends

from infrastructure.mongo import MongoDBClient
from infrastructure.mongo.landmark_cache import LandmarkCacheRepository
from infrastructure.mongo.place_raw_data import PlaceRawDataRepository
from infrastructure.mongo.property_audit import PropertyAuditRepository
from infrastructure.mongo.property import PropertyRepository
from infrastructure.mongo.search_feedback import SearchFeedbackRepository
from infrastructure.mongo.user import UserRepository


def get_db_client() -> MongoDBClient:
    return MongoDBClient()


def get_property_repository(
    client: MongoDBClient = Depends(get_db_client),
) -> PropertyRepository:
    return PropertyRepository(client=client, collection_name="property_v3")


def get_place_raw_data_repository(
    client: MongoDBClient = Depends(get_db_client),
) -> PlaceRawDataRepository:
    return PlaceRawDataRepository(client=client, collection_name="place_raw_data")


def get_property_audit_repository(
    client: MongoDBClient = Depends(get_db_client),
) -> PropertyAuditRepository:
    return PropertyAuditRepository(client=client, collection_name="property_audit_logs")


def get_user_repository(
    client: MongoDBClient = Depends(get_db_client),
) -> UserRepository:
    return UserRepository(client=client, collection_name="user")


def get_search_feedback_repository(
    client: MongoDBClient = Depends(get_db_client),
) -> SearchFeedbackRepository:
    return SearchFeedbackRepository(client=client, collection_name="search_feedback")


def get_landmark_cache_repository() -> LandmarkCacheRepository:
    return LandmarkCacheRepository(collection_name="landmark_cache")
