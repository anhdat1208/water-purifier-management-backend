from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql://waterpurifier:waterpurifier@localhost:5432/waterpurifier"
    redis_url: str = "redis://localhost:6379/0"
    secret_key: str = "change-me-to-a-long-random-secret-key"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    cors_origins: str = "http://localhost:3000"
    seed_demo_data: bool = True
    algorithm: str = "HS256"
    firebase_project_id: str = ""
    firebase_client_email: str = ""
    firebase_private_key: str = ""
    push_job_hour: int = 8
    app_timezone: str = "Asia/Ho_Chi_Minh"
    cron_secret: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def fcm_configured(self) -> bool:
        return bool(
            self.firebase_project_id.strip()
            and self.firebase_client_email.strip()
            and self.firebase_private_key.strip()
        )

    @property
    def firebase_private_key_normalized(self) -> str:
        return self.firebase_private_key.replace("\\n", "\n")


settings = Settings()
