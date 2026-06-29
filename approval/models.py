"""Data models for the approval layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Literal


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    EXECUTED = "executed"


DEFAULT_TTL_MINUTES = 15


@dataclass
class PendingAction:
    """A staged mutating action awaiting user confirmation."""

    id: str
    session_id: str
    action_name: str
    summary: str
    payload: dict[str, Any]
    created_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: datetime = field(
        default_factory=lambda: datetime.utcnow() + timedelta(minutes=DEFAULT_TTL_MINUTES)
    )
    status: ApprovalStatus = ApprovalStatus.PENDING
    destructive: bool = False
    result: dict[str, Any] | None = None

    def is_expired(self) -> bool:
        return datetime.utcnow() > self.expires_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "action_name": self.action_name,
            "summary": self.summary,
            "payload": self.payload,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
            "status": self.status.value,
            "destructive": self.destructive,
            "result": self.result,
        }
