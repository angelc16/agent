"""Constants for the campaign module."""

# Error messages
ERROR_MESSAGES = {
    "campaign_not_found": "Campaign with ID {campaign_id} not found",
    "event_not_found": "Event with ID {event_id} not found",
    "group_not_found": "Group with ID {group_id} not found",
    "invalid_date": "Event date must be in the future",
    "api_error": "External API error: {message}",
    "group_not_ready": "Group with ID {group_id} is not ready yet",
}

# API Constants
API_ENDPOINTS = {
    "campaign": "/campaign",
    "event": "/event",
    "groups": "/messaging-app/groups",
    "group_detail": "/messaging-app/groups/{group_id}",
}

# Default values
DEFAULTS = {
    "timezone": "America/Bogota",
    "event_status": "draft",
    "group_status": "pending",
}

# Metadata constants
METADATA = {
    "additional": "Additional metadata",
    "creation_timestamp": "Creation timestamp",
    "update_timestamp": "Last update timestamp",
}
