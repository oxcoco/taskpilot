"""Approval gate – stages and executes mutating actions after user confirmation."""

from __future__ import annotations

import uuid
from typing import Any

from ..actions.registry import ActionRegistry, get_registry
from .models import ApprovalStatus, PendingAction
from .store import get_store


class ApprovalGate:
  """Stages mutating actions and executes them only after explicit approval."""

  def __init__(self, registry: ActionRegistry | None = None) -> None:
    self.registry = registry or get_registry()
    self.store = get_store()

  def stage(
    self,
    session_id: str,
    action_name: str,
    payload: dict[str, Any],
    summary: str | None = None,
  ) -> PendingAction:
    spec = self.registry.get(action_name)
    if not spec.requires_approval:
      raise ValueError(f"Action {action_name!r} does not require approval")

    action = PendingAction(
      id=str(uuid.uuid4()),
      session_id=session_id,
      action_name=action_name,
      summary=summary or self.registry.summarize(action_name, payload),
      payload=payload,
      destructive=spec.destructive,
    )
    self.store.save(action)
    return action

  def approve(self, session_id: str, pending_action_id: str) -> PendingAction:
    action = self._get_pending(session_id, pending_action_id)
    action.status = ApprovalStatus.APPROVED
    result = self.registry.execute_approved(action.action_name, action.payload)
    action.result = result if isinstance(result, dict) else {"result": result}
    action.status = ApprovalStatus.EXECUTED
    self.store.update(action)
    return action

  def reject(self, session_id: str, pending_action_id: str) -> PendingAction:
    action = self._get_pending(session_id, pending_action_id)
    action.status = ApprovalStatus.REJECTED
    self.store.update(action)
    return action

  def list_pending(self, session_id: str) -> list[PendingAction]:
    pending = []
    for action in self.store.list_for_session(session_id):
      if action.is_expired():
        action.status = ApprovalStatus.EXPIRED
        self.store.update(action)
      else:
        pending.append(action)
    return pending

  def _get_pending(self, session_id: str, pending_action_id: str) -> PendingAction:
    action = self.store.get(pending_action_id)
    if not action:
      raise KeyError(f"Pending action {pending_action_id!r} not found")
    if action.session_id != session_id:
      raise PermissionError("Pending action does not belong to this session")
    if action.status != ApprovalStatus.PENDING:
      raise ValueError(f"Action is not pending (status={action.status.value})")
    if action.is_expired():
      action.status = ApprovalStatus.EXPIRED
      self.store.update(action)
      raise ValueError("Pending action has expired")
    return action
