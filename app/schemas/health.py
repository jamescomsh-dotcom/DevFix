"""Health endpoint response schema."""

from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Stable response returned by the health endpoint."""

    status: Literal["ok"]

