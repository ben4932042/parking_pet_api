from fastapi import Depends

from application.property import PropertyService
from interface.api.dependencies.db import get_property_repository


def get_property_service(repo=Depends(get_property_repository)) -> PropertyService:

    return PropertyService(repo=repo)
