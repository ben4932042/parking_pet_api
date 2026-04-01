from fastapi import Depends, APIRouter, Query
from starlette import status

from application.property import PropertyService
from application.property_note import PropertyNoteService
from application.search_history import SearchHistoryService
from application.user import UserService
from interface.api.dependencies.property_note import get_property_note_service
from interface.api.dependencies.property import get_property_service
from interface.api.dependencies.search_history import get_search_history_service
from interface.api.dependencies.user import get_user_service, get_current_user

from domain.entities import PyObjectId
from interface.api.schemas.page import Pagination
from interface.api.schemas.property import PropertyOverviewResponse
from interface.api.schemas.property_note import UserPropertyNoteListItemResponse
from interface.api.schemas.search_history import UserSearchHistoryItemResponse
from interface.api.schemas.user import (
    UserDetailResponse,
    FavoritePropertyResponse,
    FavoritePropertyStatusResponse,
)

router = APIRouter(prefix="/user")


@router.post(
    "/login", status_code=status.HTTP_200_OK, response_model=UserDetailResponse
)
async def create_new_user(
    username: str,
    service: UserService = Depends(get_user_service),
):
    return await service.basic_sign_in(name=username)


@router.patch(
    "/profile", status_code=status.HTTP_201_CREATED, response_model=UserDetailResponse
)
async def update_user_profile(
    name: str,
    service: UserService = Depends(get_user_service),
    current_user=Depends(get_current_user),
):
    return await service.update_user_profile(user_id=current_user.id, name=name)


@router.get("/me", status_code=status.HTTP_200_OK, response_model=UserDetailResponse)
async def get_me(current_user=Depends(get_current_user)):
    return current_user


@router.put(
    "/favorite/{property_id}",
    status_code=status.HTTP_200_OK,
    response_model=FavoritePropertyResponse,
)
async def update_user_favorite_property(
    property_id: PyObjectId,
    is_favorite: bool,
    service: UserService = Depends(get_user_service),
    current_user=Depends(get_current_user),
):
    user = await service.update_favorite_property(
        user_id=current_user.id,
        property_id=property_id,
        is_favorite=is_favorite,
    )
    return FavoritePropertyResponse(
        **user.model_dump(by_alias=True),
        property_id=property_id,
        is_favorite=is_favorite,
    )


@router.get(
    "/favorite/{property_id}",
    status_code=status.HTTP_200_OK,
    response_model=FavoritePropertyStatusResponse,
)
async def get_user_favorite_property_status(
    property_id: PyObjectId,
    current_user=Depends(get_current_user),
):
    return FavoritePropertyStatusResponse(
        property_id=property_id,
        is_favorite=property_id in current_user.favorite_property_ids,
    )


@router.get(
    "/favorite",
    status_code=status.HTTP_200_OK,
    response_model=list[PropertyOverviewResponse],
)
async def get_user_favorite_properties(
    current_user=Depends(get_current_user),
    property_service: PropertyService = Depends(get_property_service),
):
    properties = await property_service.get_overviews_by_ids(
        current_user.favorite_property_ids
    )
    noted_property_ids = await property_service.get_noted_property_ids(
        user_id=str(current_user.id),
        property_ids=[property_item.id for property_item in properties],
    )
    items = [
        PropertyOverviewResponse(
            **property_item.model_dump(by_alias=False),
            has_note=property_item.id in noted_property_ids,
        )
        for property_item in properties
    ]
    return sorted(items, key=lambda item: not item.has_note)


@router.get(
    "/search-history",
    status_code=status.HTTP_200_OK,
    response_model=list[UserSearchHistoryItemResponse],
)
async def get_user_search_history(
    limit: int = Query(default=20, ge=1, le=100),
    current_user=Depends(get_current_user),
    search_history_service: SearchHistoryService = Depends(get_search_history_service),
):
    items = await search_history_service.list_history(
        user_id=str(current_user.id),
        limit=limit,
    )
    return [
        UserSearchHistoryItemResponse(
            id=str(item.id),
            query=item.query,
            response_type=item.response_type,
            preferences=item.preferences,
            result_ids=item.result_ids,
            result_count=item.result_count,
            created_at=item.created_at,
        )
        for item in items
    ]


@router.get(
    "/property-notes",
    status_code=status.HTTP_200_OK,
    response_model=Pagination[UserPropertyNoteListItemResponse],
)
async def get_user_property_notes(
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    query: str | None = Query(default=None),
    current_user=Depends(get_current_user),
    note_service: PropertyNoteService = Depends(get_property_note_service),
    property_service: PropertyService = Depends(get_property_service),
):
    notes, total = await note_service.list_notes(
        user_id=str(current_user.id),
        page=page,
        size=size,
        query=query,
    )
    properties = await property_service.get_overviews_by_ids(
        [note.property_id for note in notes]
    )
    property_map = {property_item.id: property_item for property_item in properties}
    favorite_property_ids = set(current_user.favorite_property_ids)
    items = [
        UserPropertyNoteListItemResponse(
            property_id=note.property_id,
            content=note.content,
            created_at=note.created_at,
            updated_at=note.updated_at,
            property=(
                PropertyOverviewResponse(
                    **property_map[note.property_id].model_dump(by_alias=False),
                    has_note=True,
                )
                if note.property_id in property_map
                else None
            ),
        )
        for note in notes
    ]
    items = sorted(
        items, key=lambda item: item.property_id not in favorite_property_ids
    )
    pages = (total + size - 1) // size if size else 0
    return {
        "items": items,
        "total": total,
        "page": page,
        "size": size,
        "pages": pages,
    }
