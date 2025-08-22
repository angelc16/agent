"""Infrastructure layer for external API communication."""

import logging
from typing import Dict, List

import httpx
from app.core.config.settings import settings
from app.modules.campaign_module.domain.exceptions import ExternalAPIError
from app.modules.campaign_module.domain.models import (
    Campaign,
    CampaignInput,
    Event,
    EventInput,
    MessageGroup,
)

logger = logging.getLogger(__name__)


class LukiaAPIClient:
    """Client for Lukia API communication."""

    def __init__(self):
        self.base_url = settings.lukia_api_base_url
        self.headers = {
            "Authorization": f"Bearer {settings.lukia_api_token}",
            "Content-Type": "application/json",
        }

    async def create_campaign(self, campaign_data: CampaignInput) -> Campaign:
        """Create a new campaign via the external API."""
        async with httpx.AsyncClient() as client:
            try:
                payload = {
                    "name": campaign_data.name,
                    "companyId": campaign_data.company_id,
                    "messagingIntegrationId": campaign_data.integration_id,
                    "externalCampaignId": campaign_data.external_campaign_id,
                    "metadata": campaign_data.metadata,
                }
                logger.info("LukiaAPIClient.create_campaign request payload: %s", payload)

                response = await client.post(
                    f"{self.base_url}/campaign",
                    headers=self.headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                logger.info("LukiaAPIClient.create_campaign response: %s", data)
                return Campaign(**self._snake_case_keys(data))
            except httpx.HTTPStatusError as e:
                raise ExternalAPIError(
                    f"Failed to create campaign: {e.response.text}",
                    status_code=e.response.status_code,
                ) from e
            except Exception as e:
                raise ExternalAPIError(f"Unexpected error creating campaign: {str(e)}") from e

    async def create_event(self, event_data: EventInput) -> Event:
        """Create a new event via the external API."""
        async with httpx.AsyncClient() as client:
            try:
                payload = {
                    "name": event_data.name,
                    "campaignId": event_data.campaign_id,
                    "targetDate": event_data.event_date.isoformat(),
                    "targetTimezone": event_data.timezone,
                    "administrators": event_data.administrators,
                    "imageUrl": event_data.image_url,
                    "context": event_data.context,
                    "metadata": event_data.metadata,
                }
                logger.info("LukiaAPIClient.create_event request payload: %s", payload)

                response = await client.post(
                    f"{self.base_url}/event",
                    headers=self.headers,
                    json=payload,
                )
                response.raise_for_status()
                resp_json = response.json()
                logger.info("LukiaAPIClient.create_event response: %s", resp_json)
                data = resp_json.get("data", {})
                snake_data = self._snake_case_keys(data)
                return Event(**snake_data)
            except httpx.HTTPStatusError as e:
                raise ExternalAPIError(
                    f"Failed to create event: {e.response.text}",
                    status_code=e.response.status_code,
                ) from e
            except Exception as e:
                raise ExternalAPIError(f"Unexpected error creating event: {str(e)}") from e

    async def update_event_status(self, event_id: str, status: str) -> Event:
        """Update event status to trigger group creation."""
        async with httpx.AsyncClient() as client:
            try:
                payload = {"status": status}
                logger.info("LukiaAPIClient.update_event_status request: event_id=%s payload=%s", event_id, payload)

                response = await client.patch(
                    f"{self.base_url}/event/{event_id}",
                    headers=self.headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                logger.info("LukiaAPIClient.update_event_status response: %s", data)
                return Event(**self._snake_case_keys(data))
            except httpx.HTTPStatusError as e:
                raise ExternalAPIError(
                    f"Failed to update event status: {e.response.text}",
                    status_code=e.response.status_code,
                ) from e
            except Exception as e:
                raise ExternalAPIError(
                    f"Unexpected error updating event status: {str(e)}"
                ) from e

    async def get_message_groups(self, campaign_id: str) -> List[MessageGroup]:
        """Get message groups for an event."""
        async with httpx.AsyncClient() as client:
            try:
                params = {"campaignId": campaign_id}
                logger.info("LukiaAPIClient.get_message_groups request params: %s", params)

                response = await client.get(
                    f"{self.base_url}/messaging-app/groups",
                    headers=self.headers,
                    params=params,
                )
                response.raise_for_status()
                data = response.json()
                logger.info("LukiaAPIClient.get_message_groups response: %s", data)
                if isinstance(data, list):
                    return [MessageGroup(**self._snake_case_keys(item)) for item in data]
                return [MessageGroup(**self._snake_case_keys(data))]
            except httpx.HTTPStatusError as e:
                raise ExternalAPIError(
                    f"Failed to get message groups: {e.response.text}",
                    status_code=e.response.status_code,
                ) from e
            except Exception as e:
                raise ExternalAPIError(
                    f"Unexpected error getting message groups: {str(e)}"
                ) from e

    async def get_group_by_id(self, group_id: str) -> MessageGroup:
        """Get a specific message group by ID."""
        async with httpx.AsyncClient() as client:
            try:
                logger.info("LukiaAPIClient.get_group_by_id request: group_id=%s", group_id)
                response = await client.get(
                    f"{self.base_url}/messaging-app/groups",
                    headers=self.headers,
                    params={
                        "page": 1,
                        "limit": 1,
                        "search": group_id
                    }
                )
                response.raise_for_status()
                data = response.json()
                logger.info("LukiaAPIClient.get_group_by_id response: %s", data)
                message_groups = data.get("messageGroups", [])
                if not message_groups:
                    #raise ExternalAPIError(f"Group with id {group_id} not found")
                    return None

                group_data = message_groups[0]

                return MessageGroup(**self._snake_case_keys(group_data))
            except httpx.HTTPStatusError as e:
                raise ExternalAPIError(
                    f"Failed to get group: {e.response.text}",
                    status_code=e.response.status_code,
                ) from e
            except Exception as e:
                raise ExternalAPIError(f"Unexpected error getting group: {str(e)}") from e

    def _snake_case_keys(self, data: Dict) -> Dict:
        """Convert camelCase keys to snake_case."""
        if not isinstance(data, dict):
            return data

        snake_case_data = {}
        key_mapping = {
            "companyId": "company_id",
            "integrationId": "integration_id",
            "messagingIntegrationId": "integration_id",
            "externalCampaignId": "external_campaign_id",
            "campaignId": "campaign_id",
            "eventDate": "event_date",
            "targetDate": "event_date",
            "imageUrl": "image_url",
            "name": "name",
            "createdAt": "created_at",
            "admins": "administrators",
            "updatedAt": "updated_at",
            "eventId": "event_id",
            "externalId": "external_id",
            "currentParticipants": "current_participants",
        }

        for key, value in data.items():
            new_key = key_mapping.get(key, key)
            snake_case_data[new_key] = value

        return snake_case_data
