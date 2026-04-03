from typing import Optional

from pydantic import SecretStr, BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class MongoSettings(BaseModel):
    protocol: str = "mongodb"
    host: str = "localhost"
    port: Optional[int] = Field(
        default=None, description="Port number of the MongoDB server"
    )
    username: str = "user"
    password: SecretStr = SecretStr("pass")
    db_name: str = "test"

    @property
    def url(self) -> SecretStr:
        if self.port is None:
            return SecretStr(
                f"{self.protocol}://{self.username}:{self.password.get_secret_value()}@{self.host}"
            )
        else:
            return SecretStr(
                f"{self.protocol}://{self.username}:{self.password.get_secret_value()}@{self.host}:{self.port}"
            )


class GoogleSettings(BaseModel):
    project_id: str = Field(description="Google Cloud Project ID")
    location: str = Field(description="Google Cloud Location")
    service_account_file: str = Field(
        description="Path to Google Cloud Credential File"
    )
    place_api_key: SecretStr = Field(description="Google Maps API Key")


class AppleSettings(BaseModel):
    bundle_id: str = ""


class AuthSettings(BaseModel):
    signing_key: SecretStr = SecretStr("dev-unsafe-change-me")
    issuer: str = "parking-pet-api"
    access_token_ttl_seconds: int = 60 * 60
    refresh_token_ttl_seconds: int = 60 * 60 * 24 * 30


class Settings(BaseSettings):
    mongo: MongoSettings = MongoSettings()
    google: GoogleSettings
    apple: AppleSettings = AppleSettings()
    auth: AuthSettings = AuthSettings()

    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        nested_model_default_partial_update=True,
    )


settings = Settings()
