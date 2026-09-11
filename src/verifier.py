"""
Confirms a recovery action actually worked, rather than assuming success
just because the action ran without raising. This is the step that lets
the orchestrator distinguish "we tried to fix it" from "it's actually
fixed" -- a rollback that leaves the component in a degraded/failed
status, or a memory trend that's still climbing, means verification
should fail even though the recovery action itself executed cleanly.
"""

from component import Component


def verify_recovery(component: Component) -> bool:
    if component.status not in ("healthy",):
        return False
    if component.has_memory_leak():
        return False
    return True
