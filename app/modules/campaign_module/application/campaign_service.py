"""Application layer service for campaign management."""

import asyncio
from typing import List, Optional
from datetime import datetime, timezone

from app.core.config.settings import settings
from app.modules.campaign_module.domain.exceptions import (
    ExternalAPIError,
    InvalidEventDate,
)
import logging
from app.modules.campaign_module.domain.models import (
    Campaign,
    CampaignInput,
    Event,
    EventInput,
    MessageGroup,
)
from app.modules.campaign_module.infrastructure.lukia_api_client import LukiaAPIClient
import uuid
logger = logging.getLogger(__name__)


class LukiaService:
    """Service for campaign management operations."""

    def __init__(self, api_client: LukiaAPIClient = None):
        self.api_client = api_client or LukiaAPIClient()

    async def create_campaign_with_defaults(self, name: str) -> Campaign:
        """Create a campaign with default company and integration."""
        campaign_input = CampaignInput(
            name=name,
            company_id=settings.default_company,
            integration_id=settings.default_integration,
            external_campaign_id=uuid.uuid4().hex,
        )

        return await self.api_client.create_campaign(campaign_input)

    async def create_event_for_campaign(
        self,
        campaign_id: str,
        name: str,
        event_date: datetime,
        administrators: List[str],
        context: Optional[str] = None,
        tz_name: str = "America/Bogota",
    ) -> Event:
        """Create an event for a campaign."""
        base_date = event_date
        # Allow event_date passed as string: try to parse into datetime
        if isinstance(event_date, str):
            parsed = None
            # Try ISO format first
            try:
                parsed = datetime.fromisoformat(event_date)
            except Exception:
                # Try common formats
                for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d", "%d/%m/%Y %H:%M", "%d/%m/%Y"):
                    try:
                        parsed = datetime.strptime(event_date, fmt)
                        break
                    except Exception as exc:
                        logger.debug(
                            "create_event_for_campaign: failed to parse '%s' with fmt %s: %s",
                            event_date,
                            fmt,
                            exc,
                        )
            if parsed is None:
                raise InvalidEventDate(f"Invalid event_date format: {event_date}")
            event_date = parsed

        if event_date.tzinfo is None:
            event_date = event_date.replace(tzinfo=timezone.utc)
        else:
            event_date = event_date.astimezone(timezone.utc)

        # Ahora la comparación no rompe
        if event_date <= datetime.now(timezone.utc):
            logger.info(
                f"create_event_for_campaign: event_date is in the past: {event_date} and {base_date}"
            )
            raise InvalidEventDate(
                "Event date must be in the future",
                "⏰ La fecha del evento debe ser futura. Por favor, elige una fecha y hora que aún no haya pasado.",
            )


        event_input = EventInput(
            name=name,
            campaign_id=campaign_id,
            event_date=event_date,
            administrators=administrators,
            context=context,
            timezone=tz_name,
            image_url="data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==",
        )

        return await self.api_client.create_event(event_input)

    async def activate_event(self, event_id: str) -> Event:
        """Activate an event to trigger group creation."""
        payload = {"status": "scheduled"}
        logger.info(
            "CampaignService.activate_event request: event_id=%s payload=%s",
            event_id,
            payload,
        )
        return await self.api_client.update_event_status(event_id, "scheduled")

    async def get_group_status(self, group_id: str) -> MessageGroup:
        """Get the current status of a message group."""
        return await self.api_client.get_group_by_id(group_id)

    async def get_message_groups(self, event_id: str) -> List[MessageGroup]:
        """Get message groups for an event."""
        return await self.api_client.get_message_groups(event_id)

    # DEV FUNCTIONS
    async def create_complete_campaign_flow(
        self,
        campaign_name: str,
        event_name: str,
        event_date: datetime,
        administrators: List[str],
        context: Optional[str] = None,
    ) -> tuple[Campaign, Event, List[MessageGroup]]:
        """Complete flow: create campaign, event, activate and wait for groups."""
        try:
            # Step 1: Create campaign
            campaign = await self.create_campaign_with_defaults(campaign_name)

            # Step 2: Create event
            event = await self.create_event_for_campaign(
                campaign.id,
                event_name,
                event_date,
                administrators,
                context,
            )

            # Step 3: Activate event
            event = await self.activate_event(event.id)

            # Step 4: Wait for groups to be created
            groups = await self.wait_for_group_creation(event.id)

            return campaign, event, groups

        except Exception as e:
            raise ExternalAPIError(f"Failed to complete campaign flow: {str(e)}") from e

    async def wait_for_group_creation(
        self, event_id: str, max_wait_seconds: int = 120
    ) -> List[MessageGroup]:
        """Wait for WhatsApp groups to be created and return them."""
        wait_interval = 10  # Check every 10 seconds
        max_attempts = max_wait_seconds // wait_interval

        for _ in range(max_attempts):
            groups = await self.api_client.get_message_groups(event_id)

            # Check if any group has a link (is ready)
            ready_groups = [
                group for group in groups if getattr(group, "link", None) is not None
            ]
            if ready_groups:
                return ready_groups

            await asyncio.sleep(wait_interval)

        # Return groups even if not ready
        return await self.api_client.get_message_groups(event_id)
