from pydantic import SecretStr, BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict



class MongoSettings(BaseModel):
    host: str = "localhost"
    port: int = 27017
    username: str = "user"
    password: SecretStr = SecretStr("pass")
    db_name: str = "test"
    @property
    def url(self) -> SecretStr:
        return SecretStr(f"mongodb://{self.username}:{self.password.get_secret_value()}@{self.host}:{self.port}")




class Settings(BaseSettings):
    mongo: MongoSettings = MongoSettings()

    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
    )

settings = Settings()