"""Request and response schemas for Issue APIs."""
#这里面的类是用来Request and response schemas，放在routers里用

from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from app.enums import IssueStatus


class IssueCreate(BaseModel):
    """Client-controlled fields accepted by the create endpoint."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1)
    error_message: str | None = None
    ai_tool: str | None = Field(default=None, max_length=50)
    ai_prompt: str | None = None
    solution: str | None = None
    verification_notes: str | None = None

    @field_validator("title", "description", "ai_tool", mode="before")
    @classmethod
    def strip_validated_text(cls, value: object) -> object:
        """Strip fields whose length contract applies after whitespace."""
        return value.strip() if isinstance(value, str) else value


class IssueUpdate(BaseModel):
    """Client-controlled fields accepted by the partial update endpoint."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, min_length=1)
    error_message: str | None = None
    ai_tool: str | None = Field(default=None, max_length=50)
    ai_prompt: str | None = None
    solution: str | None = None
    verification_notes: str | None = None
    status: IssueStatus | None = None

    @field_validator("title", "description", "ai_tool", mode="before")
    @classmethod
    def strip_validated_text(cls, value: object) -> object:
        """Strip fields whose length contract applies after whitespace."""
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_patch_fields(self) -> "IssueUpdate":
        """Require one provided field and reject null for non-null columns."""
        if not self.model_fields_set:
            raise ValueError("PATCH 至少需要提供一个字段。")

        for field_name in ("title", "description", "status"):
            if (
                field_name in self.model_fields_set
                and getattr(self, field_name) is None
            ):
                raise ValueError(f"{field_name} 不能为 null。")

        return self


class IssueRead(BaseModel):
    """Complete Issue representation returned to API clients."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    error_message: str | None
    ai_tool: str | None
    ai_prompt: str | None
    solution: str | None
    verification_notes: str | None
    status: IssueStatus
    created_at: datetime
    updated_at: datetime
