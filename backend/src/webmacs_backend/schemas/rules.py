"""Rule (Event Engine) schemas."""

from __future__ import annotations

import datetime

from pydantic import BaseModel, Field, model_validator

from webmacs_backend.enums import RuleActionType, RuleOperator, WebhookEventType


class RuleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    event_public_id: str
    operator: RuleOperator
    threshold: float
    threshold_high: float | None = None
    action_type: RuleActionType
    webhook_event_type: WebhookEventType | None = None
    enabled: bool = True
    cooldown_seconds: int = Field(default=60, ge=0)

    @model_validator(mode="after")
    def validate_rule_consistency(self) -> RuleCreate:
        """Cross-field validation for rule configuration."""
        if self.operator in (RuleOperator.between, RuleOperator.not_between):
            if self.threshold_high is None:
                msg = "threshold_high is required for between/not_between operators"
                raise ValueError(msg)
            if self.threshold_high < self.threshold:
                msg = "threshold_high must be >= threshold"
                raise ValueError(msg)
        return self


class RuleUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    event_public_id: str | None = None
    operator: RuleOperator | None = None
    threshold: float | None = None
    threshold_high: float | None = None
    action_type: RuleActionType | None = None
    webhook_event_type: WebhookEventType | None = None
    enabled: bool | None = None
    cooldown_seconds: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def validate_rule_consistency(self) -> RuleUpdate:
        """Cross-field validation for between/not_between operators."""
        if self.operator in (RuleOperator.between, RuleOperator.not_between):
            if self.threshold is not None and self.threshold_high is None:
                msg = "threshold_high is required for between/not_between operators"
                raise ValueError(msg)
            if self.threshold is not None and self.threshold_high is not None and self.threshold_high < self.threshold:
                msg = "threshold_high must be >= threshold"
                raise ValueError(msg)
        return self


class RuleResponse(BaseModel):
    public_id: str
    name: str
    event_public_id: str
    operator: RuleOperator
    threshold: float
    threshold_high: float | None = None
    action_type: RuleActionType
    webhook_event_type: str | None = None
    enabled: bool
    cooldown_seconds: int
    last_triggered_at: datetime.datetime | None = None
    created_on: datetime.datetime | None = None
    user_public_id: str

    model_config = {"from_attributes": True}
