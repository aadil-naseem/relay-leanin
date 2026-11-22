"""Unit tests for finish_time, adjust_for_blocked, and merge_windows in core/scheduler.py and core/hazards.py."""

from __future__ import annotations

from app.core.hazards import merge_windows
from app.core.scheduler import adjust_for_blocked, finish_time


def test_finish_time_no_windows():
    assert finish_time(start=0.0, work=10.0, windows=[]) == 10.0
    assert finish_time(start=5.5, work=4.0, windows=[]) == 9.5


def test_finish_time_window_before_start():
    # Window ends before start time
    windows = [(0.0, 5.0)]
    assert finish_time(start=10.0, work=5.0, windows=windows) == 15.0


def test_finish_time_window_after_finish():
    # Window starts after work finishes
    windows = [(15.0, 20.0)]
    assert finish_time(start=0.0, work=10.0, windows=windows) == 10.0


def test_finish_time_window_overlapping_start():
    # Work arrives at t=2, but machine is down [0, 5)
    windows = [(0.0, 5.0)]
    # Machine becomes free at 5, then does 10h work -> finish at 15
    assert finish_time(start=2.0, work=10.0, windows=windows) == 15.0


def test_finish_time_window_strictly_inside_work():
    # Start at 0, work is 10h. At t=4, machine goes down until t=8 (4h downtime).
    # 0..4: 4h work. 4..8: down. 8..14: remaining 6h work. Finish = 14.
    windows = [(4.0, 8.0)]
    assert finish_time(start=0.0, work=10.0, windows=windows) == 14.0


def test_finish_time_multiple_windows():
    # Start at 0, work is 6h.
    # Downtime 1: [2, 4] -> 2h down
    # Downtime 2: [5, 7] -> 2h down
    # 0..2: 2h done (4h remain)
    # 2..4: down
    # 4..5: 1h done (3h remain)
    # 5..7: down
    # 7..10: 3h done (0 remain). Finish = 10.
    windows = [(2.0, 4.0), (5.0, 7.0)]
    assert finish_time(start=0.0, work=6.0, windows=windows) == 10.0


def test_finish_time_zero_work():
    # Zero work outside window finishes at start
    assert finish_time(start=10.0, work=0.0, windows=[(0.0, 5.0)]) == 10.0
    # Zero work inside window is delayed until window ends
    assert finish_time(start=2.0, work=0.0, windows=[(0.0, 5.0)]) == 5.0


def test_merge_windows():
    assert merge_windows([]) == []
    assert merge_windows([(1.0, 3.0)]) == [(1.0, 3.0)]
    # Overlapping
    assert merge_windows([(1.0, 4.0), (2.0, 6.0)]) == [(1.0, 6.0)]
    # Contiguous
    assert merge_windows([(1.0, 3.0), (3.0, 5.0)]) == [(1.0, 5.0)]
    # Disjoint & unsorted
    assert merge_windows([(7.0, 9.0), (1.0, 3.0)]) == [(1.0, 3.0), (7.0, 9.0)]


def test_adjust_for_blocked():
    blocked = [(10.0, 20.0), (30.0, 40.0)]
    # Outside blocked
    assert adjust_for_blocked(5.0, blocked) == 5.0
    assert adjust_for_blocked(25.0, blocked) == 25.0
    assert adjust_for_blocked(45.0, blocked) == 45.0

    # Inside blocked
    assert adjust_for_blocked(10.0, blocked) == 20.0
    assert adjust_for_blocked(15.0, blocked) == 20.0
    assert adjust_for_blocked(35.0, blocked) == 40.0
    # Right at the end edge
    assert adjust_for_blocked(20.0, blocked) == 20.0
