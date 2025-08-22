"""Telegram bot service."""

import logging
from typing import Optional

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from app.core.config.settings import settings
from app.modules.ai_module.application.ai_service import AIService
from app.modules.telegram_module.domain.models import TelegramUser

logger = logging.getLogger(__name__)


class TelegramBotService:
    """Service for managing Telegram bot interactions."""

    def __init__(self, ai_service: AIService = None):
        self.ai_service = ai_service or AIService()
        self.application: Optional[Application] = None

    async def initialize(self) -> bool:
        """Initialize the Telegram bot application."""
        if not settings.telegram_bot_token:
            logger.warning(
                "Telegram bot token not provided. Telegram bot will not be available."
            )
            return False

        try:
            # Create Application
            self.application = (
                Application.builder().token(settings.telegram_bot_token).build()
            )

            # Add handlers
            self.application.add_handler(CommandHandler("start", self._handle_start))
            self.application.add_handler(
                MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message)
            )

            logger.info("Telegram bot initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Telegram bot: {str(e)}")
            return False

    async def start_polling(self) -> None:
        """Start polling for Telegram updates."""
        if not self.application:
            logger.error("Telegram bot application not initialized")
            return

        try:
            # Initialize the application properly
            await self.application.initialize()
            # Start polling asynchronously
            await self.application.start()
            await self.application.updater.start_polling()
            logger.info("Telegram bot polling started")
        except Exception as e:
            logger.error(f"Error during Telegram polling: {str(e)}")

    async def stop(self) -> None:
        """Stop the Telegram bot."""
        if self.application:
            try:
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
                logger.info("Telegram bot stopped")
            except Exception as e:
                logger.error(f"Error stopping Telegram bot: {str(e)}")

    def _extract_user_info(self, update: Update) -> TelegramUser:
        """Extract user information from Telegram update."""
        user = update.effective_user
        return TelegramUser(
            user_id=user.id,
            first_name=user.first_name,
            last_name=user.last_name,
            username=user.username,
            language_code=user.language_code,
        )

    async def _handle_start(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle /start command."""
        user = self._extract_user_info(update)
        logger.info(f"Start command from user {user.user_id}")

        try:
            # Send welcome message
            response = await self.ai_service.process_user_message(
                str(user.user_id), "hola"
            )

            welcome_text = f"¡Hola {user.first_name}! 👋\n\n{response['message']}"

            await update.message.reply_text(welcome_text, parse_mode="HTML")

        except Exception as e:
            logger.error(f"Error handling start command: {str(e)}")
            await update.message.reply_text(
                "Lo siento, ocurrió un error. Por favor intenta de nuevo."
            )

    async def _handle_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle regular text messages."""
        user = self._extract_user_info(update)
        message_text = update.message.text

        logger.info(f"Message from user {user.user_id}: {message_text[:50]}...")

        try:
            response = await self.ai_service.process_user_message(
                str(user.user_id), message_text
            )

            # Format response for Telegram
            formatted_response = self._format_response_for_telegram(response["message"])

            await update.message.reply_text(
                formatted_response, parse_mode="HTML", disable_web_page_preview=True
            )

        except Exception as e:
            logger.error(f"Error handling message from user {user.user_id}: {str(e)}")
            await update.message.reply_text(
                "Lo siento, ocurrió un error procesando tu mensaje. Por favor intenta de nuevo."
            )

    def _format_response_for_telegram(self, text: str) -> str:
        """Format bot response for Telegram HTML parsing."""
        # Simple formatting for Telegram HTML
        # You can enhance this with more sophisticated formatting

        # Make URLs clickable (simple approach)
        import re

        url_pattern = r"https?://[^\s]+"
        text = re.sub(
            url_pattern, lambda m: f'<a href="{m.group(0)}">{m.group(0)}</a>', text
        )

        # Make phone numbers bold
        phone_pattern = r"\+\d{1,3}\s?\d{3}\s?\d{3}\s?\d{4}"
        text = re.sub(phone_pattern, lambda m: f"<b>{m.group(0)}</b>", text)

        return text
