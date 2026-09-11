# 🩹 SelfHealingSoftware

Software that **detects when one of its own components is failing and
automatically recovers** — with root-cause diagnosis, a recovery policy
per failure type, and verification that the fix actually worked.

> Systems/reliability portfolio project modeling the full loop:
> monitor → diagnose → recover → verify → record.

---

## The loop

```
Component
     ↓
Monitoring (memory trend, reported events)
     ↓
Failure detected
     ↓
Root-cause diagnosis
     ↓
Recovery policy selects an action
     ↓
Action applied (restart / rollback / retry / isolate)
     ↓
Verification (did it actually work?)
     ↓
Logged
```

## Detecting a real leak, not just "usage is high"

`component.py`'s `has_memory_leak()` requires a **sustained upward
trend** — every sample in the window monotonically non-decreasing, plus
total growth clearing a minimum threshold — not just "memory is
currently high." A busy-but-stable service with noisy-but-flat usage
correctly does not trigger it (tested directly); a service that grows
5 samples in a row does.

## Root cause before recovery, and they're separately testable

`diagnosis.py` maps symptoms to a `FailureType`; `recovery.py` maps that
failure type to the action that actually addresses its root cause —
a memory leak gets a restart (clears leaked state), a corrupted config
gets a rollback (a restart alone wouldn't fix bad config), and anything
unmapped gets **isolated** rather than guessed at, since applying the
wrong fix blind is worse than doing nothing. Keeping diagnosis and
recovery as separate modules means each is independently testable — the
same `MEMORY_LEAK` diagnosis should be reachable whether it came from a
live memory trend or an explicitly reported event.

## Recovery isn't trusted blind

`verifier.py` re-checks the component after a recovery action runs —
confirming the fix actually left the component in a healthy state,
rather than treating "the action executed without raising" as success.
A `RETRY_WITH_BACKOFF` action intentionally leaves the component
`degraded` (a retry isn't a full fix) so verification correctly reports
it as not yet resolved.

## Example

```python
from component import Component
from orchestrator import SelfHealingSystem

system = SelfHealingSystem()
service = Component(name="api-service", current_version="v2.3", known_good_version="v2.2")

for mb in [100, 105, 112, 120, 130, 142]:  # a genuine upward trend
    service.record_memory(mb)

event = system.heal(service)
print(event.failure)   # FailureType.MEMORY_LEAK
print(event.action)    # RecoveryAction.RESTART
print(event.verified)  # True
```

## Why a policy engine over hardcoded if/else per failure

Recovery logic is centralized as a `FailureType -> RecoveryAction`
mapping (`_POLICY`) rather than scattered conditionals, which is what
makes it possible to answer the interview question directly: *"I
designed a recovery policy engine that selects a recovery action based
on the observed failure and verifies whether the recovery actually
worked"* — the policy table and the verification step are both concrete,
inspectable artifacts, not just a claim.

## Tests

```bash
pip install -r requirements.txt
cd tests && python -m pytest -v
```

13 tests: stable memory usage not flagged as a leak, genuine monotonic
growth detected, small growth under threshold ignored, reported events
taking priority over an inferred memory trend, the full policy mapping
for each failure type, restart correctly clearing state, and two full
end-to-end heal cycles (memory leak, config corruption) verified as
resolved, plus a per-component queryable healing log.

## Project layout

```
src/
  component.py     # Component + memory-trend leak detection
  diagnosis.py       # symptom -> FailureType
  recovery.py          # FailureType -> RecoveryAction policy + application
  verifier.py            # post-recovery health re-check
  orchestrator.py          # full loop + evidence log
tests/
  test_selfhealingsoftware.py
```

## Honest scope

Simulated components and injected failures (intentional monotonic memory
sequences, reported event strings) rather than instrumentation of a real
running service — the architecture (diagnose → policy-driven recovery →
verify → log) is the same shape a production self-healing system would
use with real telemetry and real process control wired in underneath.
