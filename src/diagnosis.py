"""
Maps observed symptoms (a memory trend, an explicit failure event, or
both) to a specific FailureType. Kept as its own module, separate from
recovery, so the "what's wrong" question and the "what do we do about
it" question can be tested and reasoned about independently -- the same
diagnosis should be reachable whether it came from a live memory trend
or a reported crash event.
"""

from enum import Enum
from typing import Optional

from component import Component


class FailureType(Enum):
    NONE = "none"
    MEMORY_LEAK = "memory_leak"
    CRASH = "crash"
    CONFIG_CORRUPTION = "config_corruption"
    API_FAILURE = "api_failure"
    NETWORK_FAILURE = "network_failure"


# External events a caller can report (e.g. from a crash handler or an
# upstream healthcheck), independent of what the memory trend shows.
_EVENT_TO_FAILURE = {
    "crash": FailureType.CRASH,
    "config_corrupted": FailureType.CONFIG_CORRUPTION,
    "api_failure": FailureType.API_FAILURE,
    "network_failure": FailureType.NETWORK_FAILURE,
}


def diagnose(component: Component, reported_event: Optional[str] = None) -> FailureType:
    """
    Reported events take priority -- an explicit crash report is more
    certain than an inferred memory trend, and a component can only be
    healed for one root cause at a time.
    """
    if reported_event and reported_event in _EVENT_TO_FAILURE:
        return _EVENT_TO_FAILURE[reported_event]
    if component.has_memory_leak():
        return FailureType.MEMORY_LEAK
    return FailureType.NONE
