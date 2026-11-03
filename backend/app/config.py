from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Muhit o'zgaruvchilari orqali boshqariladigan sozlamalar."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "USB Qalqon API"
    app_version: str = "1.0.0"
    secret_key: str = "usb-qalqon-super-secret-key-almashtiring"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 720
    database_url: str = "sqlite:///./data/usbqalqon.db"
    cors_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,http://usbqalqon.mv,https://usbqalqon.mv,http://localhost,http://127.0.0.1"
    )

    admin_username: str = "admin"
    admin_password: str = "admin123"
    admin_full_name: str = "Tizim administratori"

    server_url: str = "http://usbqalqon.mv"

    agent_dir: str = "./data/agent"
    max_agent_package_mb: int = 200

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
