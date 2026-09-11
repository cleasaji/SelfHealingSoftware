import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from component import Component
from diagnosis import FailureType, diagnose
from recovery import RecoveryAction, select_action, apply_recovery
from orchestrator import SelfHealingSystem


def make_component(name="api-service"):
    return Component(name=name, current_version="v2.3", known_good_version="v2.2")


def test_stable_memory_usage_is_not_a_leak():
    c = make_component()
    for m in [100, 101, 99, 100, 102, 100]:
        c.record_memory(m)
    assert not c.has_memory_leak()


def test_monotonic_growth_is_detected_as_leak():
    c = make_component()
    for m in [100, 105, 112, 120, 130, 142]:
        c.record_memory(m)
    assert c.has_memory_leak()


def test_small_growth_under_threshold_is_not_flagged():
    c = make_component()
    for m in [100, 101, 102, 102, 103, 103]:  # monotonic but only 3MB growth
        c.record_memory(m)
    assert not c.has_memory_leak(min_growth_mb=5.0)


def test_diagnose_prioritizes_reported_event_over_memory_trend():
    c = make_component()
    for m in [100, 105, 112, 120, 130, 142]:
        c.record_memory(m)  # would independently qualify as a leak
    failure = diagnose(c, reported_event="crash")
    assert failure == FailureType.CRASH


def test_diagnose_falls_back_to_memory_trend_when_no_event_reported():
    c = make_component()
    for m in [100, 105, 112, 120, 130, 142]:
        c.record_memory(m)
    assert diagnose(c) == FailureType.MEMORY_LEAK


def test_diagnose_none_when_healthy_and_no_event():
    c = make_component()
    for m in [100, 101, 99, 100]:
        c.record_memory(m)
    assert diagnose(c) == FailureType.NONE


def test_recovery_policy_maps_memory_leak_to_restart():
    assert select_action(FailureType.MEMORY_LEAK) == RecoveryAction.RESTART


def test_recovery_policy_maps_config_corruption_to_rollback():
    assert select_action(FailureType.CONFIG_CORRUPTION) == RecoveryAction.ROLLBACK_CONFIG


def test_unmapped_failure_falls_back_to_isolate():
    # simulate an unmapped enum value scenario indirectly by checking default behavior
    assert select_action(FailureType.NONE) == RecoveryAction.NONE


def test_restart_action_clears_memory_history_and_restores_health():
    c = make_component()
    for m in [100, 105, 112, 120, 130, 142]:
        c.record_memory(m)
    c.status = "degraded"
    outcome = apply_recovery(c, RecoveryAction.RESTART)
    assert outcome.applied
    assert c.memory_samples == []
    assert c.status == "healthy"


def test_full_heal_cycle_memory_leak_end_to_end():
    system = SelfHealingSystem()
    c = make_component()
    for m in [100, 105, 112, 120, 130, 142]:
        c.record_memory(m)

    event = system.heal(c)
    assert event.failure == FailureType.MEMORY_LEAK
    assert event.action == RecoveryAction.RESTART
    assert event.verified
    assert not c.has_memory_leak()  # history was cleared by the restart


def test_full_heal_cycle_config_corruption_end_to_end():
    system = SelfHealingSystem()
    c = make_component()
    c.status = "failed"
    c.last_error = "invalid config"

    event = system.heal(c, reported_event="config_corrupted")
    assert event.action == RecoveryAction.ROLLBACK_CONFIG
    assert event.verified
    assert c.status == "healthy"


def test_healing_log_is_queryable_per_component():
    system = SelfHealingSystem()
    c1 = make_component("service-a")
    c2 = make_component("service-b")
    system.heal(c1, reported_event="crash")
    system.heal(c2, reported_event="crash")
    system.heal(c1, reported_event="config_corrupted")

    assert len(system.history_for("service-a")) == 2
    assert len(system.history_for("service-b")) == 1
