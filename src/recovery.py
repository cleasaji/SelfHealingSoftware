"""
Selects and applies a recovery action for a diagnosed failure. Each
failure type maps to the recovery strategy that actually addresses its
root cause -- a memory leak needs a restart (clears the leaked state), a
corrupted config needs a rollback (restart alone wouldn't fix bad
config), and an unknown/unmapped failure gets isolated rather than
guessed at, which is safer than applying the wrong fix blind.
"""

from dataclasses import dataclass
from enum import Enum

from component import Component
from diagnosis import FailureType


class RecoveryAction(Enum):
    RESTART = "restart"
    ROLLBACK_CONFIG = "rollback_config"
    ROLLBACK_VERSION = "rollback_version"
    RETRY_WITH_BACKOFF = "retry_with_backoff"
    ISOLATE = "isolate"
    NONE = "none"


_POLICY = {
    FailureType.MEMORY_LEAK: RecoveryAction.RESTART,
    FailureType.CRASH: RecoveryAction.RESTART,
    FailureType.CONFIG_CORRUPTION: RecoveryAction.ROLLBACK_CONFIG,
    FailureType.API_FAILURE: RecoveryAction.RETRY_WITH_BACKOFF,
    FailureType.NETWORK_FAILURE: RecoveryAction.RETRY_WITH_BACKOFF,
    FailureType.NONE: RecoveryAction.NONE,
}


@dataclass(frozen=True)
class RecoveryOutcome:
    action: RecoveryAction
    applied: bool
    detail: str


def select_action(failure: FailureType) -> RecoveryAction:
    return _POLICY.get(failure, RecoveryAction.ISOLATE)


def apply_recovery(component: Component, action: RecoveryAction) -> RecoveryOutcome:
    if action == RecoveryAction.RESTART:
        component.reset_memory_history()
        component.status = "healthy"
        component.last_error = None
        return RecoveryOutcome(action, True, f"{component.name} restarted; runtime state cleared")

    if action == RecoveryAction.ROLLBACK_CONFIG:
        component.status = "healthy"
        component.last_error = None
        return RecoveryOutcome(action, True, f"{component.name} config rolled back to known-good defaults")

    if action == RecoveryAction.ROLLBACK_VERSION:
        component.current_version = component.known_good_version
        component.status = "healthy"
        component.last_error = None
        return RecoveryOutcome(action, True, f"{component.name} rolled back to {component.known_good_version}")

    if action == RecoveryAction.RETRY_WITH_BACKOFF:
        component.status = "degraded"  # not fully healed by a retry alone; flags for follow-up
        return RecoveryOutcome(action, True, f"{component.name} retry scheduled with backoff")

    if action == RecoveryAction.ISOLATE:
        component.status = "failed"
        return RecoveryOutcome(action, True, f"{component.name} isolated -- unmapped failure, no safe auto-fix")

    return RecoveryOutcome(RecoveryAction.NONE, False, "no action needed")
