"""Tests for the TimeExtensionAlgorithm — pure math, no TraCI needed."""
from flowsense.simulation.algorithm import TimeExtensionAlgorithm


# ---------------------------------------------------------------------------
#  Dynamic max-green scaling
# ---------------------------------------------------------------------------

def test_dynamic_max_green_full_queue():
    algo = TimeExtensionAlgorithm(min_green=10.0, max_green=50.0, max_queue_capacity=30)
    # Full queue → effective_max_green == max_green
    assert algo.calculate_dynamic_max_green(30) == 50.0


def test_dynamic_max_green_empty_queue():
    algo = TimeExtensionAlgorithm(min_green=10.0, max_green=50.0, max_queue_capacity=30)
    # Empty queue → effective_max_green == min_green
    assert algo.calculate_dynamic_max_green(0) == 10.0


def test_dynamic_max_green_half_queue():
    algo = TimeExtensionAlgorithm(min_green=10.0, max_green=50.0, max_queue_capacity=30)
    # Half queue → midpoint
    result = algo.calculate_dynamic_max_green(15)
    assert result == 30.0  # 10 + 0.5 * (50 - 10) = 30


def test_dynamic_max_green_over_capacity_capped():
    algo = TimeExtensionAlgorithm(min_green=10.0, max_green=50.0, max_queue_capacity=30)
    # Over capacity → capped at max_green
    assert algo.calculate_dynamic_max_green(100) == 50.0


# ---------------------------------------------------------------------------
#  Gap-Out detection
# ---------------------------------------------------------------------------

def test_gap_out_after_min_green():
    algo = TimeExtensionAlgorithm(min_green=10.0, max_green=50.0)
    # Simulate 10 seconds of green (100 steps at 0.1s)
    for _ in range(100):
        should, reason = algo.decide_yellow_transition(0.1, vehicles_detected=5, is_healthy=True, queue_count=10)
    # Now at 10.0s exactly, with zero vehicles → should gap-out
    should, reason = algo.decide_yellow_transition(0.1, vehicles_detected=0, is_healthy=True, queue_count=0)
    assert should is True
    assert "GAP-OUT" in reason


def test_no_gap_out_before_min_green():
    algo = TimeExtensionAlgorithm(min_green=10.0, max_green=50.0)
    # Only 5 seconds elapsed
    for _ in range(50):
        should, reason = algo.decide_yellow_transition(0.1, vehicles_detected=5, is_healthy=True)
    # Zero vehicles but before min_green → keep
    should, reason = algo.decide_yellow_transition(0.1, vehicles_detected=0, is_healthy=True)
    assert should is False
    assert reason == "KEEP"


def test_no_gap_out_unhealthy_camera():
    algo = TimeExtensionAlgorithm(min_green=10.0, max_green=50.0)
    # Exceed min_green, use queue_count=30 to increase effective_max_green to 50
    for _ in range(110):
        algo.decide_yellow_transition(0.1, vehicles_detected=5, is_healthy=True, queue_count=30)
    # Zero vehicles but camera unhealthy → don't gap-out (failsafe)
    should, reason = algo.decide_yellow_transition(0.1, vehicles_detected=0, is_healthy=False, queue_count=30)
    assert should is False


# ---------------------------------------------------------------------------
#  Max-Out detection
# ---------------------------------------------------------------------------

def test_max_out_at_dynamic_limit():
    algo = TimeExtensionAlgorithm(min_green=10.0, max_green=50.0, max_queue_capacity=30)
    # With queue_count=0, effective max = min_green = 10.0
    # After 10s with vehicles still present → should max-out
    for _ in range(100):
        should, reason = algo.decide_yellow_transition(0.1, vehicles_detected=5, is_healthy=True, queue_count=0)
    should, reason = algo.decide_yellow_transition(0.1, vehicles_detected=5, is_healthy=True, queue_count=0)
    assert should is True
    assert "MAX-OUT" in reason


def test_max_out_at_full_capacity():
    algo = TimeExtensionAlgorithm(min_green=10.0, max_green=50.0, max_queue_capacity=30)
    # With queue_count=30 (full), effective max = 50.0
    # Vehicles keep flowing, should not max-out at 20s
    for _ in range(200):
        should, reason = algo.decide_yellow_transition(0.1, vehicles_detected=5, is_healthy=True, queue_count=30)
    assert should is False
    # But should max-out after 50s total
    for _ in range(300):
        should, reason = algo.decide_yellow_transition(0.1, vehicles_detected=5, is_healthy=True, queue_count=30)
    assert should is True
    assert "MAX-OUT" in reason


# ---------------------------------------------------------------------------
#  Phase Skipping / next direction selection
# ---------------------------------------------------------------------------

def test_select_next_skips_empty_directions():
    algo = TimeExtensionAlgorithm()
    algo.current_direction = "N"
    direction_phases = {
        "N": {"green": 0, "yellow": 1},
        "S": {"green": 4, "yellow": 5},
        "E": {"green": 2, "yellow": 3},
        "W": {"green": 6, "yellow": 7},
    }
    counterpart = {"N": "S", "S": "N", "E": "W", "W": "E"}

    # Only West has queue
    def get_queue(d):
        return 10 if d == "W" else 0

    next_dir = algo.select_next_direction(
        is_dual_mode=False,
        direction_phases=direction_phases,
        counterpart=counterpart,
        get_queue_fn=get_queue,
    )
    assert next_dir == "W"


def test_select_next_keeps_current_when_all_empty():
    algo = TimeExtensionAlgorithm()
    algo.current_direction = "N"
    direction_phases = {
        "N": {"green": 0, "yellow": 1},
        "S": {"green": 4, "yellow": 5},
        "E": {"green": 2, "yellow": 3},
        "W": {"green": 6, "yellow": 7},
    }
    counterpart = {"N": "S", "S": "N", "E": "W", "W": "E"}

    next_dir = algo.select_next_direction(
        is_dual_mode=False,
        direction_phases=direction_phases,
        counterpart=counterpart,
        get_queue_fn=lambda d: 0,
    )
    assert next_dir == "N"  # Stays on current


# ---------------------------------------------------------------------------
#  Starvation prevention
# ---------------------------------------------------------------------------

def test_starvation_boosts_long_waiting_direction():
    algo = TimeExtensionAlgorithm(starvation_threshold=120.0)
    algo.current_direction = "N"

    direction_phases = {
        "N": {"green": 0, "yellow": 1},
        "S": {"green": 4, "yellow": 5},
        "E": {"green": 2, "yellow": 3},
        "W": {"green": 6, "yellow": 7},
    }
    counterpart = {"N": "S", "S": "N", "E": "W", "W": "E"}

    # Simulate South has been on red for 180 seconds (> starvation_threshold)
    algo.accumulated_red_time["S"] = 180.0
    algo.accumulated_red_time["E"] = 10.0
    algo.accumulated_red_time["W"] = 10.0

    # East has more vehicles but South has starvation bonus
    # S: queue=5, weight=1+(180/120)=2.5, score=12.5
    # E: queue=8, weight=1+(10/120)=1.083, score=8.67
    def get_queue(d):
        return {"S": 5, "E": 8, "W": 2}.get(d, 0)

    next_dir = algo.select_next_direction(
        is_dual_mode=False,
        direction_phases=direction_phases,
        counterpart=counterpart,
        get_queue_fn=get_queue,
    )
    assert next_dir == "S"  # South wins due to starvation weight


# ---------------------------------------------------------------------------
#  Emergency Vehicle Preemption (EVP)
# ---------------------------------------------------------------------------

def test_evp_activates():
    algo = TimeExtensionAlgorithm()
    result = algo.handle_evp_request("E", cooldown_seconds=10.0)
    assert result is True
    assert algo.evp_active is True
    assert algo.evp_direction == "E"
    assert algo.evp_cooldown_remaining == 10.0


def test_evp_blocked_during_cooldown():
    algo = TimeExtensionAlgorithm()
    algo.handle_evp_request("E", cooldown_seconds=10.0)
    algo.evp_active = False
    algo.evp_direction = None
    # Cooldown still active
    result = algo.handle_evp_request("W", cooldown_seconds=10.0)
    assert result is False


def test_evp_cooldown_ticks_down():
    algo = TimeExtensionAlgorithm()
    algo.handle_evp_request("E", cooldown_seconds=10.0)
    algo.tick_evp_cooldown(5.0)
    assert algo.evp_cooldown_remaining == 5.0
    algo.tick_evp_cooldown(5.0)
    assert algo.evp_cooldown_remaining == 0.0
    # Now cooldown is over, should accept new EVP
    algo.evp_active = False
    algo.evp_direction = None
    result = algo.handle_evp_request("W", cooldown_seconds=10.0)
    assert result is True


# ---------------------------------------------------------------------------
#  Input validation
# ---------------------------------------------------------------------------

def test_invalid_min_green_raises():
    import pytest
    with pytest.raises(ValueError, match="min_green"):
        TimeExtensionAlgorithm(min_green=0)


def test_invalid_max_green_raises():
    import pytest
    with pytest.raises(ValueError, match="max_green"):
        TimeExtensionAlgorithm(min_green=10, max_green=5)


def test_invalid_yellow_raises():
    import pytest
    with pytest.raises(ValueError, match="yellow_duration"):
        TimeExtensionAlgorithm(yellow_duration=0)
