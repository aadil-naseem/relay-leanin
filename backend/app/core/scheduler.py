"""M5 list scheduler with downtime windows (blueprint section 7.3). Pure logic.

Implements deterministic Earliest-Due-Date (EDD) list scheduling with machine and
vendor resources, supplier lead time, and pre-emptive resume finish_time around
downtime windows.

Key rules:
  - Time unit: float hours from now (t = 0.0).
  - Shift hours: wall_clock_factor = 24.0 / shift_hours_per_day converts in-house
    working hours (qty * hours_per_unit + setup_hours) to elapsed wall-clock hours.
  - Step sequencing: for each order, steps run in `seq` order.
  - Machine selection: an in-house step is scheduled on the capable machine yielding
    the earliest finish time; tie-breaker is machine_id lexicographical.
  - Outsourced steps: assigned to a capable vendor. Total elapsed time is:
      handoff_ready -> [delayed if site access blocked]
      -> transport_hours to vendor -> vendor turnaround (with vendor downtime)
      -> transport_hours back to factory -> [delayed if site access blocked].
  - Material arrival: if an approved supplier exists for the order's material,
      material_ready = finish_time(0.0, supplier.turnaround_hours, supplier_windows)
      -> delayed if factory access is blocked at arrival.
      If no approved supplier, material is considered in-stock (0.0 h).
  - Dispatch blocking: if factory access is blocked when the final step completes,
      dispatch is delayed until the block clears.
  - Two runs: baseline (empty downtime) vs stressed (hazard downtime).

No database or FastAPI imports.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from app.core.hazards import DowntimeWindows
from app.enums import FallbackLevel, OrderState, ProcessCode

FallbackResolver = Callable[["OrderScheduleInput"], tuple[FallbackLevel, str | None]]


@dataclass(frozen=True)
class StepScheduleInput:
    step_id: str
    seq: int
    process: ProcessCode
    hours_per_unit: float
    setup_hours: float
    tolerance_mm: float | None = None
    envelope_mm: float | None = None
    outsourced: bool = False


@dataclass(frozen=True)
class OrderScheduleInput:
    order_id: str
    part_id: str
    part_name: str
    qty: int
    due_in_hours: float
    value_inr: float
    material: str
    steps: tuple[StepScheduleInput, ...] = ()


@dataclass(frozen=True)
class MachineScheduleInput:
    id: str
    process: ProcessCode
    tolerance_mm: float | None = None
    envelope_mm: float | None = None
    available: bool = True


@dataclass(frozen=True)
class VendorScheduleInput:
    id: str
    process: ProcessCode
    turnaround_hours: float
    available: bool = True


@dataclass(frozen=True)
class SupplierScheduleInput:
    id: str
    material: str
    turnaround_hours: float
    available: bool = True


@dataclass(frozen=True)
class StepScheduleResult:
    step_id: str
    seq: int
    process: ProcessCode
    assigned_resource_id: str
    start_time: float
    finish_time: float
    outsourced: bool


@dataclass(frozen=True)
class OrderScheduleResult:
    order_id: str
    part_id: str
    due_in_hours: float
    finish_time: float
    value_inr: float
    step_results: tuple[StepScheduleResult, ...] = ()


@dataclass(frozen=True)
class ScheduleRunResult:
    orders: dict[str, OrderScheduleResult] = field(default_factory=dict)
    machine_busy_until: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class OrderStressEvaluation:
    order_id: str
    part_id: str
    state: OrderState
    due_in_hours: float
    baseline_finish_hours: float
    stressed_finish_hours: float
    days_late: float | None
    value_inr: float
    fallback_level: FallbackLevel = FallbackLevel.NONE
    best_backup: str | None = None


@dataclass(frozen=True)
class StressSimulationResult:
    orders: tuple[OrderStressEvaluation, ...]
    orders_at_risk: int
    revenue_exposed_inr: float
    orders_no_fallback: int
    orders_no_ready_fallback: int
    affected_sites: tuple[str, ...]
    affected_resources: tuple[str, ...]
    baseline_run: ScheduleRunResult
    stressed_run: ScheduleRunResult


def finish_time(start: float, work: float, windows: list[tuple[float, float]]) -> float:
    """Pre-emptive resume finish time given non-working downtime windows (section 7.3)."""
    t, remaining = float(start), float(work)
    for s, e in windows:
        if e <= t:
            continue
        if s > t:
            avail = s - t
            if remaining <= avail:
                return t + remaining
            remaining -= avail
        t = max(t, e)
    return t + remaining


def adjust_for_blocked(t: float, blocked_windows: list[tuple[float, float]]) -> float:
    """If time t lands strictly inside any blocked window [s, e), delay it to e."""
    curr = float(t)
    for s, e in blocked_windows:
        if s <= curr < e:
            curr = e
    return curr


def machine_can_serve_step(step: StepScheduleInput, machine: MachineScheduleInput) -> bool:
    """Check if machine matches step process, achievable tolerance, and envelope."""
    if not machine.available or step.outsourced:
        return False
    if machine.process != step.process:
        return False
    if step.tolerance_mm is not None and machine.tolerance_mm is not None:
        if machine.tolerance_mm > step.tolerance_mm:
            return False
    if step.envelope_mm is not None and machine.envelope_mm is not None:
        if machine.envelope_mm < step.envelope_mm:
            return False
    return True


def schedule_orders(
    orders: list[OrderScheduleInput],
    factory_id: str,
    shift_hours_per_day: float,
    machines: list[MachineScheduleInput],
    vendors: list[VendorScheduleInput],
    suppliers: list[SupplierScheduleInput],
    downtime: DowntimeWindows,
    transport_hours: float = 4.0,
) -> ScheduleRunResult:
    """Execute list scheduling across all orders in Earliest-Due-Date order."""
    wall_clock_factor = 24.0 / max(1.0, min(24.0, float(shift_hours_per_day)))
    factory_blocked = downtime.site_blocked_windows.get(factory_id, [])

    # Order scheduling sequence: EDD, tie-breaker order_id
    sorted_orders = sorted(orders, key=lambda o: (o.due_in_hours, o.order_id))

    # Track resource availability
    machine_free_at: dict[str, float] = {m.id: 0.0 for m in machines}
    order_results: dict[str, OrderScheduleResult] = {}

    for order in sorted_orders:
        current_time = 0.0

        # Step 0: Material arrival
        matching_suppliers = [s for s in suppliers if s.available and s.material == order.material]
        if matching_suppliers:
            # Pick first available matching supplier
            supplier = matching_suppliers[0]
            sup_windows = downtime.resource_windows.get(supplier.id, [])
            mat_ready = finish_time(0.0, supplier.turnaround_hours, sup_windows)
            current_time = adjust_for_blocked(mat_ready, factory_blocked)
        else:
            # Material in stock; check if factory access blocked at t=0
            current_time = adjust_for_blocked(0.0, factory_blocked)

        step_results: list[StepScheduleResult] = []

        # Steps in sequential order
        sorted_steps = sorted(order.steps, key=lambda s: s.seq)
        for step in sorted_steps:
            if not step.outsourced:
                # In-house step on machines
                capable_machines = [m for m in machines if machine_can_serve_step(step, m)]
                work = (order.qty * step.hours_per_unit) + step.setup_hours
                elapsed_work = work * wall_clock_factor

                if capable_machines:
                    # Evaluate each machine and pick the one with earliest finish
                    best_m: MachineScheduleInput | None = None
                    best_finish = float("inf")
                    best_start = float("inf")

                    for m in sorted(capable_machines, key=lambda x: x.id):
                        cand_start = max(current_time, machine_free_at[m.id])
                        m_windows = downtime.resource_windows.get(m.id, [])
                        cand_finish = finish_time(cand_start, elapsed_work, m_windows)

                        if cand_finish < best_finish:
                            best_finish = cand_finish
                            best_start = cand_start
                            best_m = m

                    assert best_m is not None
                    machine_free_at[best_m.id] = best_finish
                    current_time = best_finish
                    step_results.append(
                        StepScheduleResult(
                            step_id=step.step_id,
                            seq=step.seq,
                            process=step.process,
                            assigned_resource_id=best_m.id,
                            start_time=best_start,
                            finish_time=best_finish,
                            outsourced=False,
                        )
                    )
                else:
                    # No machine capable - assign fallback dummy time
                    step_results.append(
                        StepScheduleResult(
                            step_id=step.step_id,
                            seq=step.seq,
                            process=step.process,
                            assigned_resource_id="UNASSIGNED",
                            start_time=current_time,
                            finish_time=current_time,
                            outsourced=False,
                        )
                    )

            else:
                # Outsourced step to a vendor
                capable_vendors = [v for v in vendors if v.available and v.process == step.process]
                if capable_vendors:
                    # Pick vendor yielding earliest return
                    best_v: VendorScheduleInput | None = None
                    best_return = float("inf")
                    best_depart = float("inf")

                    for v in sorted(capable_vendors, key=lambda x: x.id):
                        depart = adjust_for_blocked(current_time, factory_blocked)
                        arrive_vendor = depart + transport_hours
                        v_windows = downtime.resource_windows.get(v.id, [])
                        v_finish = finish_time(arrive_vendor, v.turnaround_hours, v_windows)
                        arrive_back = adjust_for_blocked(v_finish + transport_hours, factory_blocked)

                        if arrive_back < best_return:
                            best_return = arrive_back
                            best_depart = depart
                            best_v = v

                    assert best_v is not None
                    current_time = best_return
                    step_results.append(
                        StepScheduleResult(
                            step_id=step.step_id,
                            seq=step.seq,
                            process=step.process,
                            assigned_resource_id=best_v.id,
                            start_time=best_depart,
                            finish_time=best_return,
                            outsourced=True,
                        )
                    )
                else:
                    step_results.append(
                        StepScheduleResult(
                            step_id=step.step_id,
                            seq=step.seq,
                            process=step.process,
                            assigned_resource_id="UNASSIGNED",
                            start_time=current_time,
                            finish_time=current_time,
                            outsourced=True,
                        )
                    )

        # Final order dispatch check
        final_finish = adjust_for_blocked(current_time, factory_blocked)
        order_results[order.order_id] = OrderScheduleResult(
            order_id=order.order_id,
            part_id=order.part_id,
            due_in_hours=order.due_in_hours,
            finish_time=final_finish,
            value_inr=order.value_inr,
            step_results=tuple(step_results),
        )

    return ScheduleRunResult(orders=order_results, machine_busy_until=machine_free_at)


def run_stress_simulation(
    orders: list[OrderScheduleInput],
    factory_id: str,
    shift_hours_per_day: float,
    machines: list[MachineScheduleInput],
    vendors: list[VendorScheduleInput],
    suppliers: list[SupplierScheduleInput],
    downtime: DowntimeWindows,
    due_buffer_hours: float = 24.0,
    transport_hours: float = 4.0,
    fallback_resolver: FallbackResolver | None = None,
) -> StressSimulationResult:
    """Run baseline and stressed schedules, compare against due dates, and summarize."""
    # 1. Baseline run (no downtime windows)
    baseline_run = schedule_orders(
        orders=orders,
        factory_id=factory_id,
        shift_hours_per_day=shift_hours_per_day,
        machines=machines,
        vendors=vendors,
        suppliers=suppliers,
        downtime=DowntimeWindows(),
        transport_hours=transport_hours,
    )

    # 2. Stressed run (with hazard downtime windows)
    stressed_run = schedule_orders(
        orders=orders,
        factory_id=factory_id,
        shift_hours_per_day=shift_hours_per_day,
        machines=machines,
        vendors=vendors,
        suppliers=suppliers,
        downtime=downtime,
        transport_hours=transport_hours,
    )

    # 3. Evaluate each order
    evaluations: list[OrderStressEvaluation] = []
    orders_at_risk = 0
    revenue_exposed_inr = 0.0

    # Retain input order for predictable report presentation
    for order in orders:
        base_res = baseline_run.orders.get(order.order_id)
        base_finish = base_res.finish_time if base_res else 0.0

        str_res = stressed_run.orders.get(order.order_id)
        str_finish = str_res.finish_time if str_res else 0.0

        due = order.due_in_hours

        if str_finish > due:
            state = OrderState.LATE
            days_late = round((str_finish - due) / 24.0, 2)
        elif str_finish >= (due - due_buffer_hours):
            state = OrderState.AT_RISK
            days_late = None
        else:
            state = OrderState.ON_TRACK
            days_late = None

        if state in (OrderState.LATE, OrderState.AT_RISK):
            orders_at_risk += 1
            revenue_exposed_inr += order.value_inr

        fallback_level = FallbackLevel.NONE
        best_backup = None
        if fallback_resolver is not None:
            fallback_level, best_backup = fallback_resolver(order)

        evaluations.append(
            OrderStressEvaluation(
                order_id=order.order_id,
                part_id=order.part_id,
                state=state,
                due_in_hours=due,
                baseline_finish_hours=base_finish,
                stressed_finish_hours=str_finish,
                days_late=days_late,
                value_inr=order.value_inr,
                fallback_level=fallback_level,
                best_backup=best_backup,
            )
        )

    orders_no_fallback = sum(
        1
        for o in evaluations
        if o.state in (OrderState.LATE, OrderState.AT_RISK) and o.fallback_level == FallbackLevel.NONE
    )
    orders_no_ready_fallback = sum(
        1
        for o in evaluations
        if o.state in (OrderState.LATE, OrderState.AT_RISK) and o.fallback_level != FallbackLevel.READY
    )

    return StressSimulationResult(
        orders=tuple(evaluations),
        orders_at_risk=orders_at_risk,
        revenue_exposed_inr=revenue_exposed_inr,
        orders_no_fallback=orders_no_fallback,
        orders_no_ready_fallback=orders_no_ready_fallback,
        affected_sites=downtime.affected_sites,
        affected_resources=downtime.affected_resources,
        baseline_run=baseline_run,
        stressed_run=stressed_run,
    )
