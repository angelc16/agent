"""Domain exceptions for the campaign module."""


class CampaignError(Exception):
    """Base exception for campaign-related errors."""

class InvalidEventDate(CampaignError):
    """Exception raised when an event date is invalid."""

    def __init__(self, message: str, bot_message: str = None):
        super().__init__(message)
        self.bot_message = bot_message or message


class GroupNotFound(CampaignError):
    """Exception raised when a group is not found."""

    def __init__(self, group_id: str):
        self.group_id = group_id
        super().__init__(f"Group with ID {group_id} not found")


class ExternalAPIError(CampaignError):
    """Exception raised when external API calls fail."""

    def __init__(self, message: str, status_code: int = None):
        self.status_code = status_code
        super().__init__(message)
