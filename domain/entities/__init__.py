from typing import Annotated
from pydantic import BeforeValidator, PlainSerializer, WithJsonSchema


PyObjectId = Annotated[
    str,
    BeforeValidator(lambda v: str(v)),  # 進入模型前強制轉字串
    PlainSerializer(lambda v: str(v), return_type=str),  # 出模型後強制轉字串
    WithJsonSchema({"type": "string", "example": "65f1a2b3c4d5e6f7a8b9c0d1"}),
]
