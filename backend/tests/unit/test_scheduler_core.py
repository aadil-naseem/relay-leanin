"""Unit tests for core/scheduler.py: list scheduling, EDD ordering, machine assignment, vendor steps."""

from __future__ import annotations

from app.core.hazards import DowntimeWindows
from app.core.scheduler import (
    MachineScheduleInput,
    OrderScheduleInput,
    StepScheduleInput,
    SupplierScheduleInput,
    VendorScheduleInput,
    run_stress_simulation,
    schedule_orders,
)
from app.enums import OrderState, ProcessCode


def test_hand_computed_two_order_example():
    """Deterministic hand-computed scenario to verify baseline vs stressed arithmetic."""
    # Machine: 1 lathe
    machines = [
        MachineScheduleInput(id="mch_turn_1", process=ProcessCode.TURN, tolerance_mm=0.05, available=True)
    ]

    # Two orders
    orders = [
        OrderScheduleInput(
            order_id="ord_1",
            part_id="prt_1",
            part_name="Shaft A",
            qty=10,
            due_in_hours=5.0,
            value_inr=100000.0,
            material="EN8",
            steps=(
                StepScheduleInput(
                    step_id="step_1_1",
                    seq=1,
                    process=ProcessCode.TURN,
                    hours_per_unit=0.1,  # 10 * 0.1 = 1.0 h work
                    setup_hours=0.0,
                    tolerance_mm=0.05,
                    outsourced=False,
                ),
            ),
        ),
        OrderScheduleInput(
            order_id="ord_2",
            part_id="prt_2",
            part_name="Shaft B",
            qty=20,
            due_in_hours=8.0,
            value_inr=200000.0,
            material="EN8",
            steps=(
                StepScheduleInput(
                    step_id="step_2_1",
                    seq=1,
                    process=ProcessCode.TURN,
                    hours_per_unit=0.1,  # 20 * 0.1 = 2.0 h work
                    setup_hours=0.0,
                    tolerance_mm=0.05,
                    outsourced=False,
                ),
            ),
        ),
    ]

    # Downtime: mch_turn_1 down from t=0.5 to t=6.5 (6.0 h outage)
    downtime = DowntimeWindows(
        resource_windows={"mch_turn_1": [(0.5, 6.5)]},
        site_blocked_windows={},
        affected_sites=("fac_owner",),
        affected_resources=("mch_turn_1",),
    )

    result = run_stress_simulation(
        orders=orders,
        factory_id="fac_owner",
        shift_hours_per_day=24.0,  # 1.0 wall clock factor
        machines=machines,
        vendors=[],
        suppliers=[],
        downtime=downtime,
        due_buffer_hours=2.0,
        transport_hours=4.0,
    )

    # 1. Baseline assertions:
    # ord_1 runs 0.0 -> 1.0 (due at 5.0 -> ON_TRACK)
    # ord_2 runs 1.0 -> 3.0 (due at 8.0 -> ON_TRACK)
    base_1 = result.baseline_run.orders["ord_1"]
    base_2 = result.baseline_run.orders["ord_2"]
    assert base_1.finish_time == 1.0
    assert base_2.finish_time == 3.0

    # 2. Stressed assertions:
    # ord_1: 0.0..0.5 (0.5 done, 0.5 remain). Outage 0.5..6.5. Resumes 6.5..7.0 -> finishes 7.0!
    # Stressed finish (7.0) > Due (5.0) -> LATE, 2.0 hours late = 0.08 days.
    # ord_2: starts at 7.0 (when machine becomes free). Runs 7.0..9.0 -> finishes 9.0!
    # Stressed finish (9.0) > Due (8.0) -> LATE, 1.0 hour late = 0.04 days.
    str_1 = result.stressed_run.orders["ord_1"]
    str_2 = result.stressed_run.orders["ord_2"]
    assert str_1.finish_time == 7.0
    assert str_2.finish_time == 9.0

    eval_by_id = {o.order_id: o for o in result.orders}
    assert eval_by_id["ord_1"].state == OrderState.LATE
    assert eval_by_id["ord_1"].days_late == 0.08
    assert eval_by_id["ord_2"].state == OrderState.LATE
    assert eval_by_id["ord_2"].days_late == 0.04

    # 3. Summary assertions:
    assert result.orders_at_risk == 2
    assert result.revenue_exposed_inr == 300000.0
    assert result.orders_no_fallback == 2
    assert result.orders_no_ready_fallback == 2


def test_edd_ordering_schedule_priority():
    """Orders with earlier due dates must be scheduled first."""
    machines = [
        MachineScheduleInput(id="mch_turn_1", process=ProcessCode.TURN, available=True)
    ]

    # Order A arrives first in list but is due later (t=20h)
    order_a = OrderScheduleInput(
        order_id="ord_late_due",
        part_id="prt_1",
        part_name="Part 1",
        qty=10,
        due_in_hours=20.0,
        value_inr=10000.0,
        material="EN8",
        steps=(
            StepScheduleInput(
                step_id="s_1", seq=1, process=ProcessCode.TURN, hours_per_unit=1.0, setup_hours=0.0
            ),
        ),
    )
    # Order B arrives second in list but is due earlier (t=5h)
    order_b = OrderScheduleInput(
        order_id="ord_early_due",
        part_id="prt_2",
        part_name="Part 2",
        qty=5,
        due_in_hours=5.0,
        value_inr=10000.0,
        material="EN8",
        steps=(
            StepScheduleInput(
                step_id="s_2", seq=1, process=ProcessCode.TURN, hours_per_unit=1.0, setup_hours=0.0
            ),
        ),
    )

    run = schedule_orders(
        orders=[order_a, order_b],
        factory_id="fac_1",
        shift_hours_per_day=24.0,
        machines=machines,
        vendors=[],
        suppliers=[],
        downtime=DowntimeWindows(),
    )

    # Order B is scheduled FIRST because its due date is earlier
    res_b = run.orders["ord_early_due"]
    assert res_b.finish_time == 5.0  # 5 units * 1.0 h = 5.0 h

    # Order A is scheduled SECOND
    res_a = run.orders["ord_late_due"]
    assert res_a.finish_time == 15.0  # 5.0 + (10 * 1.0 h) = 15.0 h


def test_earliest_finish_machine_selection():
    """When multiple machines are capable, the scheduler assigns the one that finishes earliest."""
    # Machine 1 is already busy until t=8.0; Machine 2 is idle (busy until 0.0)
    machines = [
        MachineScheduleInput(id="mch_turn_busy", process=ProcessCode.TURN, available=True),
        MachineScheduleInput(id="mch_turn_idle", process=ProcessCode.TURN, available=True),
    ]

    # Pre-downtime to simulate Machine 1 busy
    downtime = DowntimeWindows(
        resource_windows={"mch_turn_busy": [(0.0, 8.0)]},
        site_blocked_windows={},
    )

    order = OrderScheduleInput(
        order_id="ord_1",
        part_id="prt_1",
        part_name="Part 1",
        qty=2,
        due_in_hours=20.0,
        value_inr=10000.0,
        material="EN8",
        steps=(
            StepScheduleInput(
                step_id="s_1", seq=1, process=ProcessCode.TURN, hours_per_unit=2.0, setup_hours=0.0
            ),
        ),
    )

    run = schedule_orders(
        orders=[order],
        factory_id="fac_1",
        shift_hours_per_day=24.0,
        machines=machines,
        vendors=[],
        suppliers=[],
        downtime=downtime,
    )

    res = run.orders["ord_1"]
    # Step was assigned to idle machine (mch_turn_idle) finishing at t=4.0 rather than busy machine finishing at t=12.0
    assigned_m = res.step_results[0].assigned_resource_id
    assert assigned_m == "mch_turn_idle"
    assert res.finish_time == 4.0


def test_outsourced_vendor_step_with_downtime():
    """Outsourced steps use transport (4h) + vendor turnaround + return transport (4h)."""
    vendors = [
        VendorScheduleInput(id="ven_heat_1", process=ProcessCode.HEAT_TREAT, turnaround_hours=24.0, available=True)
    ]

    order = OrderScheduleInput(
        order_id="ord_heat",
        part_id="prt_heat",
        part_name="Hardened Pin",
        qty=10,
        due_in_hours=50.0,
        value_inr=50000.0,
        material="EN8",
        steps=(
            StepScheduleInput(
                step_id="step_ht", seq=1, process=ProcessCode.HEAT_TREAT, hours_per_unit=0.0, setup_hours=0.0, outsourced=True
            ),
        ),
    )

    # Baseline: depart at 0 -> 4h travel -> arrive at 4 -> 24h work -> done at 28 -> 4h return -> back at 32h!
    base_run = schedule_orders(
        orders=[order],
        factory_id="fac_1",
        shift_hours_per_day=24.0,
        machines=[],
        vendors=vendors,
        suppliers=[],
        downtime=DowntimeWindows(),
        transport_hours=4.0,
    )
    assert base_run.orders["ord_heat"].finish_time == 32.0

    # Stressed: vendor has 10h downtime [10.0, 20.0]
    # Arrives at vendor at 4h. Works 4..10 (6h done, 18h remain). Outage 10..20. Resumes 20..38.
    # Return travel 4h: 38 + 4 = 42h!
    downtime = DowntimeWindows(
        resource_windows={"ven_heat_1": [(10.0, 20.0)]},
        site_blocked_windows={},
    )
    str_run = schedule_orders(
        orders=[order],
        factory_id="fac_1",
        shift_hours_per_day=24.0,
        machines=[],
        vendors=vendors,
        suppliers=[],
        downtime=downtime,
        transport_hours=4.0,
    )
    assert str_run.orders["ord_heat"].finish_time == 42.0


def test_supplier_material_lead_time_delays_order():
    """If an approved supplier has turnaround_hours, production cannot start before material arrives."""
    suppliers = [
        SupplierScheduleInput(id="sup_steel_1", material="EN24", turnaround_hours=48.0, available=True)
    ]
    machines = [
        MachineScheduleInput(id="mch_turn_1", process=ProcessCode.TURN, available=True)
    ]

    order = OrderScheduleInput(
        order_id="ord_mat",
        part_id="prt_en24",
        part_name="Heavy Pin",
        qty=1,
        due_in_hours=100.0,
        value_inr=50000.0,
        material="EN24",
        steps=(
            StepScheduleInput(
                step_id="step_turn", seq=1, process=ProcessCode.TURN, hours_per_unit=2.0, setup_hours=0.0
            ),
        ),
    )

    # Baseline: material arrives at t=48.0 -> machining 2.0h -> finishes at 50.0h
    base_run = schedule_orders(
        orders=[order],
        factory_id="fac_1",
        shift_hours_per_day=24.0,
        machines=machines,
        vendors=[],
        suppliers=suppliers,
        downtime=DowntimeWindows(),
    )
    assert base_run.orders["ord_mat"].finish_time == 50.0


def test_access_blocked_delays_dispatch():
    """If the factory exit is blocked when production completes, dispatch is delayed."""
    machines = [
        MachineScheduleInput(id="mch_turn_1", process=ProcessCode.TURN, available=True)
    ]

    order = OrderScheduleInput(
        order_id="ord_1",
        part_id="prt_1",
        part_name="Part 1",
        qty=1,
        due_in_hours=20.0,
        value_inr=10000.0,
        material="EN8",
        steps=(
            StepScheduleInput(
                step_id="s_1", seq=1, process=ProcessCode.TURN, hours_per_unit=5.0, setup_hours=0.0
            ),
        ),
    )

    # Machine runs 0..5h. But factory access is blocked [4.0, 14.0].
    # Dispatch cannot happen at 5h -> delayed to 14h!
    downtime = DowntimeWindows(
        resource_windows={},
        site_blocked_windows={"fac_1": [(4.0, 14.0)]},
    )

    run = schedule_orders(
        orders=[order],
        factory_id="fac_1",
        shift_hours_per_day=24.0,
        machines=machines,
        vendors=[],
        suppliers=[],
        downtime=downtime,
    )
    assert run.orders["ord_1"].finish_time == 14.0
