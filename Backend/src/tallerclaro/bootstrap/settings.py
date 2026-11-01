from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="TALLERCLARO_", extra="ignore")

    app_name: str = "TallerClaro API"
