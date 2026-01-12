from typing import Any, Dict

from pydantic import BaseModel, ConfigDict, Field


class StripeEvent(BaseModel):
    """
    Minimal Stripe event fields. Allow extra keys.
    """
    model_config = ConfigDict(extra="allow")

    id: str
    type: str
    created: int
    data: Dict[str, Any] = Field(default_factory=dict)
