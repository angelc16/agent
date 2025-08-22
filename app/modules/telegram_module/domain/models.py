"""Telegram bot models and types."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TelegramUser(BaseModel):
    """Telegram user information."""

    user_id: int = Field(..., description="Telegram user ID")
    first_name: str = Field(..., description="User's first name")
    last_name: Optional[str] = Field(default=None, description="User's last name")
    username: Optional[str] = Field(default=None, description="User's username")
    language_code: Optional[str] = Field(
        default=None, description="User's language code"
    )


class TelegramMessage(BaseModel):
    """Telegram message structure."""

    message_id: int = Field(..., description="Telegram message ID")
    user: TelegramUser = Field(..., description="Message sender")
    text: str = Field(..., description="Message text")
    timestamp: datetime = Field(default_factory=datetime.now)


class TelegramBotResponse(BaseModel):
    """Response structure for Telegram bot."""

    text: str = Field(..., description="Response text to send")
    parse_mode: Optional[str] = Field(default="HTML", description="Parse mode for formatting")
    reply_markup: Optional[dict] = Field(default=None, description="Keyboard markup")
    disable_web_page_preview: bool = Field(
        default=True, description="Disable web page preview"
    )
