from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = (
        "postgresql+psycopg2://ledger:ledgerpass@localhost:5432/ledgerlock"
    )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()