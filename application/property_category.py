from domain.entities.property_category import (
    PROPERTY_CATEGORIES,
    get_categories_by_primary_type,
    PropertyCategoryEntity,
    PropertyCategoryMatchEntity,
)
from interface.api.exceptions.error import NotFoundError

class PropertyCategoryService:
    def __init__(self, categories: list[PropertyCategoryEntity] | None = None):
        self.categories = categories or PROPERTY_CATEGORIES

    def list_categories(self) -> list[PropertyCategoryEntity]:
        return self.categories

    def get_categories_by_primary_type(self, primary_type: str) -> PropertyCategoryMatchEntity:
        matched = get_categories_by_primary_type(primary_type)
        if not matched:
            raise NotFoundError(f"Unknown primary type: {primary_type}")
        return PropertyCategoryMatchEntity(primary_type=primary_type, categories=matched)
