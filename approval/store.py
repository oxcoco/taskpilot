"""In-memory store for pending approval actions."""

from __future__ import annotations

from typing import Dict, List, Optional

from .models import ApprovalStatus, PendingAction


class ApprovalStore:
  """Thread-unsafe in-memory store (sufficient for local dev)."""

  def __init__(self) -> None:
    self._actions: Dict[str, PendingAction] = {}

  def save(self, action: PendingAction) -> None:
    self._actions[action.id] = action

  def get(self, action_id: str) -> Optional[PendingAction]:
    return self._actions.get(action_id)

  def list_for_session(self, session_id: str) -> List[PendingAction]:
    return [
      a
      for a in self._actions.values()
      if a.session_id == session_id and a.status == ApprovalStatus.PENDING
    ]

  def update(self, action: PendingAction) -> None:
    self._actions[action.id] = action

  def clear(self) -> None:
    self._actions.clear()


# Module-level singleton used by the gate and API.
_store = ApprovalStore()


def get_store() -> ApprovalStore:
  return _store
