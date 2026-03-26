from domain.entities.user import UserEntity


class UserDetailResponse(UserEntity):
    model_config = {"from_attributes": True}
