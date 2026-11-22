"""Hypothesis property tests for core/scheduler.py (blueprint task 6).

Invariants verified:
  1. Stressed finish >= Baseline finish under any valid downtime windows (for dedicated/single-machine routing).
  2. No machine double-booked (no two steps run on the same machine at overlapping intervals).
  3. Step order respected (step i+1 start >= step i finish).
"""

from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from app.core.hazards import DowntimeWindows
from app.core.scheduler import (
    MachineScheduleInput,
    OrderScheduleInput,
    StepScheduleInput,
    run_stress_simulation,
)
from app.enums import ProcessCode


@st.composite
def random_simulation_world(draw, multi_machine: bool = False):
    """Generate a random collection of orders, steps, machines, and downtime windows."""
    if multi_machine:
        machines = [
            MachineScheduleInput(id="mch_turn_1", process=ProcessCode.TURN, available=True),
            MachineScheduleInput(id="mch_turn_2", process=ProcessCode.TURN, available=True),
            MachineScheduleInput(id="mch_mill_1", process=ProcessCode.MILL, available=True),
            MachineScheduleInput(id="mch_mill_2", process=ProcessCode.MILL, available=True),
        ]
    else:
        machines = [
            MachineScheduleInput(id="mch_turn_1", process=ProcessCode.TURN, available=True),
            MachineScheduleInput(id="mch_mill_1", process=ProcessCode.MILL, available=True),
        ]

    num_orders = draw(st.integers(min_value=1, max_value=5))
    orders: list[OrderScheduleInput] = []

    for i in range(num_orders):
        order_id = f"ord_{i}"
        due_in_hours = draw(st.floats(min_value=5.0, max_value=100.0))
        value_inr = draw(st.floats(min_value=1000.0, max_value=500000.0))

        # 1 to 2 steps per order
        num_steps = draw(st.integers(min_value=1, max_value=2))
        steps: list[StepScheduleInput] = []

        processes = [ProcessCode.TURN, ProcessCode.MILL]
        for s_idx in range(num_steps):
            step_id = f"step_{i}_{s_idx}"
            proc = processes[s_idx]
            hpu = draw(st.floats(min_value=0.1, max_value=2.0))
            setup = draw(st.floats(min_value=0.0, max_value=1.0))
            steps.append(
                StepScheduleInput(
                    step_id=step_id,
                    seq=s_idx + 1,
                    process=proc,
                    hours_per_unit=hpu,
                    setup_hours=setup,
                    outsourced=False,
                )
            )

        orders.append(
            OrderScheduleInput(
                order_id=order_id,
                part_id=f"prt_{i}",
                part_name=f"Part {i}",
                qty=draw(st.integers(min_value=1, max_value=10)),
                due_in_hours=due_in_hours,
                value_inr=value_inr,
                material="EN8",
                steps=tuple(steps),
            )
        )

    # Random downtime windows for machines
    res_windows: dict[str, list[tuple[float, float]]] = {}
    for m in machines:
        has_down = draw(st.booleans())
        if has_down:
            w_start = draw(st.floats(min_value=0.0, max_value=20.0))
            w_dur = draw(st.floats(min_value=1.0, max_value=30.0))
            res_windows[m.id] = [(w_start, w_start + w_dur)]

    downtime = DowntimeWindows(
        resource_windows=res_windows,
        site_blocked_windows={},
    )

    return orders, machines, downtime


@settings(max_examples=100, deadline=None)
@given(world=random_simulation_world(multi_machine=False))
def test_monotonic_delay_single_machine(world):
    """Invariant 1: Stressed finish >= Baseline finish for dedicated/single machine routing."""
    orders, machines, downtime = world

    result = run_stress_simulation(
        orders=orders,
        factory_id="fac_test",
        shift_hours_per_day=16.0,
        machines=machines,
        vendors=[],
        suppliers=[],
        downtime=downtime,
        due_buffer_hours=24.0,
        transport_hours=4.0,
    )

    for order in orders:
        base_res = result.baseline_run.orders[order.order_id]
        str_res = result.stressed_run.orders[order.order_id]
        assert str_res.finish_time >= base_res.finish_time - 1e-9


@settings(max_examples=100, deadline=None)
@given(world=random_simulation_world(multi_machine=True))
def test_scheduler_safety_and_integrity_multi_machine(world):
    """Invariants 2 & 3: No machine double-booked and step order respected across multiple machines."""
    orders, machines, downtime = world

    result = run_stress_simulation(
        orders=orders,
        factory_id="fac_test",
        shift_hours_per_day=16.0,
        machines=machines,
        vendors=[],
        suppliers=[],
        downtime=downtime,
        due_buffer_hours=24.0,
        transport_hours=4.0,
    )

    # Invariant 2: No machine double-booked in baseline or stressed run
    for run in (result.baseline_run, result.stressed_run):
        machine_intervals: dict[str, list[tuple[float, float, str, str]]] = {}
        for ord_id, ord_res in run.orders.items():
            for s_res in ord_res.step_results:
                if not s_res.outsourced and s_res.assigned_resource_id != "UNASSIGNED":
                    machine_intervals.setdefault(s_res.assigned_resource_id, []).append(
                        (s_res.start_time, s_res.finish_time, ord_id, s_res.step_id)
                    )

        for m_id, intervals in machine_intervals.items():
            sorted_ints = sorted(intervals, key=lambda x: (x[0], x[1]))
            for idx in range(len(sorted_ints) - 1):
                cur_start, cur_end, cur_ord, _ = sorted_ints[idx]
                nxt_start, nxt_end, nxt_ord, _ = sorted_ints[idx + 1]
                assert nxt_start >= cur_end - 1e-9, (
                    f"Machine {m_id} double-booked between order {cur_ord} (end {cur_end}) "
                    f"and order {nxt_ord} (start {nxt_start})"
                )

    # Invariant 3: Step order respected within each order
    for run in (result.baseline_run, result.stressed_run):
        for ord_id, ord_res in run.orders.items():
            step_results = sorted(ord_res.step_results, key=lambda s: s.seq)
            for idx in range(len(step_results) - 1):
                cur_step = step_results[idx]
                nxt_step = step_results[idx + 1]
                assert nxt_step.start_time >= cur_step.finish_time - 1e-9, (
                    f"Order {ord_id} steps out of order: step {cur_step.seq} finished at {cur_step.finish_time}, "
                    f"but step {nxt_step.seq} started at {nxt_step.start_time}"
                )
