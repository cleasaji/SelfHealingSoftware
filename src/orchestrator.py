"""
Ties diagnosis, recovery, and verification into the full self-healing
loop, and keeps an evidence log of every healing attempt -- so "how does
it know what to do" has a concrete, inspectable answer: a recorded chain
of failure -> action -> verified outcome per attempt, not a black box.
"""

from dataclasses import dataclass
from typing import List, Optional

from component import Component
from diagnosis import FailureType, diagnose
from recovery import RecoveryAction, RecoveryOutcome, select_action, apply_recovery
from verifier import verify_recovery


@dataclass(frozen=True)
class HealingEvent:
    component_name: str
    failure: FailureType
    action: RecoveryAction
    recovery_detail: str
    verified: bool


class SelfHealingSystem:
    def __init__(self) -> None:
        self.log: List[HealingEvent] = []

    def heal(self, component: Component, reported_event: Optional[str] = None) -> HealingEvent:
        failure = diagnose(component, reported_event)
        action = select_action(failure)
        outcome: RecoveryOutcome = apply_recovery(component, action)
        verified = verify_recovery(component) if failure != FailureType.NONE else True

        event = HealingEvent(
            component_name=component.name,
            failure=failure,
            action=action,
            recovery_detail=outcome.detail,
            verified=verified,
        )
        self.log.append(event)
        return event

    def history_for(self, component_name: str) -> List[HealingEvent]:
        return [e for e in self.log if e.component_name == component_name]
