from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Настройки приложения, загружаемые из переменных окружения"""

    # Polza.ai API настройки
    POLZA_API_KEY: str = "pza_EOg9XmG-vdpv_AdKokT1ZfQhdJdpZxbS"
    POLZA_API_URL: str = "https://api.polza.ai/api/v1"
    POLZA_MODEL: str = "deepseek/deepseek-v3.2"

    # Настройки приложения
    APP_NAME: str = "AI Content Generator"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Настройки сервера
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )


# Создаем глобальный экземпляр настроек
settings = Settings()