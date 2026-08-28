"""Declarative base and shared UTC clock for database models."""

from datetime import UTC, datetime

from sqlalchemy.orm import DeclarativeBase


def utc_now() -> datetime:
    """Return naive UTC for storage in MySQL DATETIME columns."""
    return datetime.now(UTC).replace(tzinfo=None)


class Base(DeclarativeBase):
    """Base class for all DevFix SQLAlchemy models."""

