from typing import Optional

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Configuration
    lukia_api_base_url: str = Field(
        default="https://dev-api.lukia.marketing", env="LUKIA_API_BASE_URL"
    )
    lukia_api_token: str = Field(..., env="LUKIA_API_TOKEN")

    # OpenAI Configuration
    openai_api_key: str = Field(..., env="OPENAI_API_KEY")

    # Telegram Configuration
    telegram_bot_token: Optional[str] = Field(default=None, env="TELEGRAM_BOT_TOKEN")

    # FastAPI Configuration
    api_host: str = Field(default="127.0.0.1", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    debug: bool = Field(default=False, env="DEBUG")

    # Default Campaign Configuration
    default_company: str = Field(default="Okolo", env="DEFAULT_COMPANY")
    default_integration: str = Field(
        default="Lukia Whapi DEV", env="DEFAULT_INTEGRATION"
    )

    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
