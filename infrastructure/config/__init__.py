from typing import Optional

from pydantic import SecretStr, BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict



class MongoSettings(BaseModel):
    protocol: str = "mongodb"
    host: str = "localhost"
    port: Optional[int] = Field(default=None, description="Port number of the MongoDB server")
    username: str = "user"
    password: SecretStr = SecretStr("pass")
    db_name: str = "test"
    @property
    def url(self) -> SecretStr:
        if self.port is None:
            return SecretStr(f"{self.protocol}://{self.username}:{self.password.get_secret_value()}@{self.host}")
        else:
            return SecretStr(f"{self.protocol}://{self.username}:{self.password.get_secret_value()}@{self.host}:{self.port}")




class Settings(BaseSettings):
    mongo: MongoSettings = MongoSettings()

    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
    )

settings = Settings()