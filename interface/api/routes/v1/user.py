from fastapi import Depends, APIRouter, Query
from starlette import status

from application.apple_auth import AppleAuthService
from application.auth_session import AuthSessionService
from application.exceptions import ApplicationError
from application.property import PropertyService
from application.property_note import PropertyNoteService
from application.user import UserService
from interface.api.dependencies.property_note import get_property_note_service
from interface.api.dependencies.property import get_property_service
from interface.api.dependencies.user import (
    get_apple_auth_service,
    get_auth_session_service,
    get_user_service,
    get_current_user,
)

from domain.entities import PyObjectId
from interface.api.exceptions.error import from_application_error
from interface.api.schemas.page import Pagination
from interface.api.schemas.property import PropertyOverviewResponse
from interface.api.schemas.property_note import UserPropertyNoteListItemResponse
from interface.api.schemas.search_history import UserSearchHistoryItemResponse
from interface.api.schemas.user import (
    UserAuthSessionResponse,
    UserDetailResponse,
    UserAuthStatusResponse,
    FavoritePropertyResponse,
    FavoritePropertyStatusResponse,
    AppleAuthRequest,
    RegisterBasicUserRequest,
    UpdateUserProfileRequest,
    UserProfileResponse,
    UserDeleteResponse,
    RefreshTokenRequest,
    LogoutResponse,
)

router = APIRouter(prefix="/user")


@router.post(
    "/auth/apple",
    status_code=status.HTTP_200_OK,
    response_model=UserAuthSessionResponse,
    summary="Authenticate with Apple",
    description=(
        "Verifies the Apple identity token, resolves or creates the corresponding user, "
        "restores a previously soft-deleted Apple account when applicable, "
        "and returns a bearer-token session."
    ),
)
async def authenticate_with_apple(
    payload: AppleAuthRequest,
    service: AppleAuthService = Depends(get_apple_auth_service),
    auth_session_service: AuthSessionService = Depends(get_auth_session_service),
):
    try:
        user = await service.authenticate(
            identity_token=payload.identity_token,
            authorization_code=payload.authorization_code,
            user_identifier=payload.user_identifier,
            email=payload.email,
            name=payload.name,
            pet_name=payload.pet_name,
        )
        session = await auth_session_service.start_session(user=user)
        return UserAuthSessionResponse(
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            user=UserDetailResponse.model_validate(session.user),
        )
    except ApplicationError as exc:
        raise from_application_error(exc)


@router.post(
    "/register",
    status_code=status.HTTP_200_OK,
    response_model=UserAuthSessionResponse,
    summary="Register basic user",
    description=(
        "Creates a basic user account with name and optional pet name, "
        "then immediately starts an authenticated bearer-token session."
    ),
)
async def register_basic_user(
    payload: RegisterBasicUserRequest,
    service: UserService = Depends(get_user_service),
    auth_session_service: AuthSessionService = Depends(get_auth_session_service),
):
    user = await service.register_basic_user(
        name=payload.name,
        pet_name=payload.pet_name,
    )
    session = await auth_session_service.start_session(user=user)
    return UserAuthSessionResponse(
        access_token=session.access_token,
        refresh_token=session.refresh_token,
        user=UserDetailResponse.model_validate(session.user),
    )


@router.post(
    "/auth/refresh",
    status_code=status.HTTP_200_OK,
    response_model=UserAuthSessionResponse,
    summary="Refresh auth session",
    description=(
        "Exchanges a valid refresh token for a new access token, a rotated refresh token, "
        "and the latest user snapshot."
    ),
)
async def refresh_user_session(
    payload: RefreshTokenRequest,
    auth_session_service: AuthSessionService = Depends(get_auth_session_service),
):
    try:
        session = await auth_session_service.refresh_session(
            refresh_token=payload.refresh_token
        )
        return UserAuthSessionResponse(
            access_token=session.access_token,
            refresh_token=session.refresh_token,
            user=UserDetailResponse.model_validate(session.user),
        )
    except ApplicationError as exc:
        raise from_application_error(exc)


@router.post(
    "/auth/logout",
    status_code=status.HTTP_200_OK,
    response_model=LogoutResponse,
    summary="Logout current session",
    description=(
        "Revokes the current authenticated session. "
        "Requires `Authorization: Bearer <access_token>`."
    ),
)
@router.post(
    "/auth/revoke",
    status_code=status.HTTP_200_OK,
    response_model=LogoutResponse,
    include_in_schema=False,
)
async def logout_user(
    auth_session_service: AuthSessionService = Depends(get_auth_session_service),
    current_user=Depends(get_current_user),
):
    try:
        await auth_session_service.logout(user_id=str(current_user.id))
        return LogoutResponse(revoked=True)
    except ApplicationError as exc:
        raise from_application_error(exc)


@router.get(
    "/profile",
    status_code=status.HTTP_200_OK,
    response_model=UserProfileResponse,
    summary="Get current user profile",
    description="Returns the profile for the authenticated user.",
)
async def get_user_profile(current_user=Depends(get_current_user)):
    return current_user


@router.patch(
    "/profile",
    status_code=status.HTTP_200_OK,
    response_model=UserProfileResponse,
    summary="Update current user profile",
    description=(
        "Updates the authenticated user's display name and optional pet name."
    ),
)
async def update_user_profile(
    payload: UpdateUserProfileRequest,
    service: UserService = Depends(get_user_service),
    current_user=Depends(get_current_user),
):
    return await service.update_user_profile(
        user_id=current_user.id,
        name=payload.name,
        pet_name=payload.pet_name,
    )


@router.get(
    "/me",
    status_code=status.HTTP_200_OK,
    response_model=UserAuthStatusResponse,
    summary="Check auth status",
    description=(
        "Validates the bearer token and returns whether it maps to an active user session."
    ),
)
async def get_me(current_user=Depends(get_current_user)):
    return UserAuthStatusResponse(authenticated=current_user is not None)


@router.put(
    "/favorite/{property_id}",
    status_code=status.HTTP_200_OK,
    response_model=FavoritePropertyResponse,
    summary="Add or remove favorite property",
    description=(
        "Updates the authenticated user's favorite state for a property. "
        "Use the `is_favorite` query parameter to add or remove the favorite."
    ),
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
    summary="Get favorite status",
    description="Returns whether the authenticated user has favorited the target property.",
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
    summary="List favorite properties",
    description=(
        "Returns the authenticated user's favorite properties as property overviews. "
        "Items with user notes are prioritized first."
    ),
)
async def get_user_favorite_properties(
    current_user=Depends(get_current_user),
    property_service: PropertyService = Depends(get_property_service),
):
    favorite_property_ids = set(current_user.favorite_property_ids)
    noted_property_ids = {note.property_id for note in current_user.property_notes}
    properties = await property_service.get_overviews_by_ids(
        current_user.favorite_property_ids
    )
    items = [
        PropertyOverviewResponse(
            **property_item.model_dump(by_alias=False),
            has_note=property_item.id in noted_property_ids,
            is_favorite=property_item.id in favorite_property_ids,
        )
        for property_item in properties
    ]
    return sorted(items, key=lambda item: not item.has_note)


@router.get(
    "/search-history",
    status_code=status.HTTP_200_OK,
    response_model=list[UserSearchHistoryItemResponse],
    summary="List search history",
    description=(
        "Returns the authenticated user's recent search history, newest first."
    ),
)
async def get_user_search_history(
    limit: int = Query(default=20, ge=1, le=100),
    current_user=Depends(get_current_user),
):
    items = current_user.recent_searches[:limit]
    return [
        UserSearchHistoryItemResponse(
            query=item.query,
            searched_at=item.searched_at,
        )
        for item in items
    ]


@router.delete(
    "",
    status_code=status.HTTP_200_OK,
    response_model=UserDeleteResponse,
    summary="Soft-delete current user account",
    description=(
        "Soft-deletes the authenticated user account by marking it deleted. "
        "User data is retained, but existing bearer-token authentication becomes invalid."
    ),
)
async def delete_current_user(
    service: UserService = Depends(get_user_service),
    current_user=Depends(get_current_user),
):
    deleted = await service.delete_user(current_user.id)
    return UserDeleteResponse(user_id=current_user.id, deleted=deleted)


@router.get(
    "/property-notes",
    status_code=status.HTTP_200_OK,
    response_model=Pagination[UserPropertyNoteListItemResponse],
    summary="List current user's property notes",
    description=(
        "Returns paginated private notes for the authenticated user, "
        "including related property overviews when available."
    ),
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
    noted_property_ids = {note.property_id for note in notes}
    items = [
        UserPropertyNoteListItemResponse(
            property_id=note.property_id,
            content=note.content,
            created_at=note.created_at,
            updated_at=note.updated_at,
            property=(
                PropertyOverviewResponse(
                    **property_map[note.property_id].model_dump(by_alias=False),
                    has_note=note.property_id in noted_property_ids,
                    is_favorite=note.property_id in favorite_property_ids,
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
