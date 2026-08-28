"""Shared business enums for DevFix."""

from enum import StrEnum


class IssueStatus(StrEnum):
    """Allowed lifecycle states for an issue."""

    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
