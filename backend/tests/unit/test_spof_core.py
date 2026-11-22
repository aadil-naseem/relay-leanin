"""Phase 6: M3 SPOF core (blueprint section 7.1).

(a) hand-built graphs with known SPOFs;
(b) hypothesis property test against an independent brute-force
    "remove each resource and re-check" implementation.
The seeded-world assertions live in tests/api/test_spof_api.py.
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.core.spof import (
    KIND_MACHINE,
    KIND_SUPPLIER,
    KIND_VENDOR,
    OrderRequirement,
    Resource,
    StepRequirement,
    find_spofs,
    servers_for_material,
    servers_for_step,
)
from app.enums import ProcessCode


def machine(machine_id: str, process: ProcessCode, tolerance: float | None = 0.02, **kwargs) -> Resource:
    return Resource(
        id=machine_id,
        kind=KIND_MACHINE,
        name=machine_id,
        site_id=kwargs.pop("site_id", "fac_owner"),
        process=process,
        tolerance_mm=tolerance,
        envelope_mm=kwargs.pop("envelope_mm", 500.0),
        **kwargs,
    )


def vendor(vendor_id: str, process: ProcessCode, **kwargs) -> Resource:
    return Resource(
        id=vendor_id,
        kind=KIND_VENDOR,
        name=vendor_id,
        site_id=kwargs.pop("site_id", vendor_id),
        process=process,
        **kwargs,
    )


def supplier(supplier_id: str, material: str, **kwargs) -> Resource:
    return Resource(
        id=supplier_id, kind=KIND_SUPPLIER, name=supplier_id, site_id=kwargs.pop("site_id", supplier_id),
        material=material, **kwargs,
    )


def step(step_id: str, seq: int, process: ProcessCode, tolerance: float | None = None, outsourced: bool = False):
    return StepRequirement(step_id=step_id, seq=seq, process=process, tolerance_mm=tolerance, outsourced=outsourced)


def order(order_id: str, value: float, material: str, steps: tuple[StepRequirement, ...]) -> OrderRequirement:
    return OrderRequirement(
        order_id=order_id, part_id=f"part_{order_id}", part_name=f"Part {order_id}",
        value_inr=value, material=material, steps=steps,
    )


# ---------------------------------------------------------------- (a) hand-built


def test_three_lathes_are_never_an_spof():
    resources = [machine(f"lathe_{i}", ProcessCode.TURN) for i in (1, 2, 3)]
    resources += [supplier("steel_a", "EN8"), supplier("steel_b", "EN8")]  # material itself never a SPOF
    orders = [order("o1", 100_000.0, "EN8", (step("s1", 1, ProcessCode.TURN, 0.02),))]
    result = find_spofs(orders, resources)
    assert result.items == ()
    assert result.uncovered_requirements == ()


def test_lone_grinder_is_an_spof_with_revenue():
    resources = [
        *[machine(f"lathe_{i}", ProcessCode.TURN) for i in (1, 2, 3)],
        machine("grinder", ProcessCode.GRIND_CYL, tolerance=0.005),
    ]
    orders = [
        order("o1", 1_200_000.0, "EN24", (
            step("s1", 1, ProcessCode.TURN, 0.02),
            step("s2", 2, ProcessCode.GRIND_CYL, 0.005),
        )),
    ]
    result = find_spofs(orders, resources)
    assert [item.resource_id for item in result.items] == ["grinder"]
    item = result.items[0]
    assert item.orders_broken == ("o1",)
    assert item.steps_broken == ("s2",)
    assert item.revenue_at_risk_inr == pytest.approx(1_200_000.0)
    assert item.rank == 1


def test_ranking_is_revenue_then_order_count_then_id():
    resources = [machine("only_grinder", ProcessCode.GRIND_CYL, 0.005), vendor("only_heat", ProcessCode.HEAT_TREAT)]
    orders = [
        order("big", 900_000.0, "EN24", (
            step("b1", 1, ProcessCode.GRIND_CYL, 0.005),
            step("b2", 2, ProcessCode.HEAT_TREAT, outsourced=True),
        )),
        order("small_a", 100_000.0, "EN24", (step("a1", 1, ProcessCode.GRIND_CYL, 0.005),)),
        order("small_b", 100_000.0, "EN24", (step("c1", 1, ProcessCode.GRIND_CYL, 0.005),)),
    ]
    result = find_spofs(orders, resources)
    # both cover "big"; grinder covers 3 orders vs vendor 1 -> grinder first at equal revenue
    assert result.items[0].resource_id == "only_grinder"
    assert result.items[0].revenue_at_risk_inr == pytest.approx(1_100_000.0)
    assert result.items[1].resource_id == "only_heat"
    assert result.items[1].revenue_at_risk_inr == pytest.approx(900_000.0)
    assert [item.rank for item in result.items] == [1, 2]


def test_tolerance_filter_blocks_an_incapable_machine():
    resources = [machine("loose_grinder", ProcessCode.GRIND_CYL, tolerance=0.02)]
    resources += [supplier("steel_a", "EN24"), supplier("steel_b", "EN24")]
    orders = [order("o1", 500_000.0, "EN24", (step("s1", 1, ProcessCode.GRIND_CYL, 0.005),))]
    result = find_spofs(orders, resources)
    assert result.items == ()  # cannot hold 0.005, so it is not a server at all
    assert len(result.uncovered_requirements) == 1
    assert "step 1 GRIND_CYL" in result.uncovered_requirements[0]
    assert "no approved server" in result.uncovered_requirements[0]


def test_envelope_filter_blocks_a_too_small_machine():
    resources = [machine("small_vmc", ProcessCode.MILL, tolerance=0.02, envelope_mm=200.0)]
    big = StepRequirement(step_id="s1", seq=1, process=ProcessCode.MILL, tolerance_mm=0.02, envelope_mm=400.0)
    orders = [order("o1", 1.0, "EN8", (big,))]
    assert find_spofs(orders, resources).items == ()


def test_unavailable_machine_does_not_serve():
    resources = [machine("lathe", ProcessCode.TURN, available=False)]
    orders = [order("o1", 1.0, "EN8", (step("s1", 1, ProcessCode.TURN, 0.02),))]
    result = find_spofs(orders, resources)
    assert result.items == ()
    assert result.excluded_resources == ("lathe",)


def test_outsourced_flag_routes_work_to_vendors_only():
    resources = [machine("in_house_heat", ProcessCode.HEAT_TREAT), vendor("heat_vendor", ProcessCode.HEAT_TREAT)]
    outsourced = order("o1", 10.0, "EN8", (step("s1", 1, ProcessCode.HEAT_TREAT, outsourced=True),))
    in_house = order("o2", 20.0, "EN8", (step("s2", 1, ProcessCode.HEAT_TREAT),))
    assert servers_for_step(outsourced.steps[0], resources) == frozenset({"heat_vendor"})
    assert servers_for_step(in_house.steps[0], resources) == frozenset({"in_house_heat"})


def test_supplier_is_a_spof_and_material_must_match():
    resources = [supplier("steel_en24", "EN24"), supplier("steel_en8", "EN8")]
    orders = [
        order("o1", 300_000.0, "EN24", (step("s1", 1, ProcessCode.TURN, 0.02),)),
        order("o2", 700_000.0, "SS304", (step("s2", 1, ProcessCode.TURN, 0.02),)),
    ]
    result = find_spofs(orders, resources)
    assert [item.resource_id for item in result.items] == ["steel_en24"]
    assert result.items[0].revenue_at_risk_inr == pytest.approx(300_000.0)
    # SS304 has no approved supplier: reported, not blamed on a resource
    assert any("SS304" in line for line in result.uncovered_requirements)


def test_exposed_flag_marks_zone_sites():
    resources = [
        machine("grinder", ProcessCode.GRIND_CYL, 0.005, site_id="fac_owner"),
        vendor("heat", ProcessCode.HEAT_TREAT, site_id="ven_heat"),
    ]
    orders = [
        order("o1", 1.0, "EN24", (
            step("s1", 1, ProcessCode.GRIND_CYL, 0.005),
            step("s2", 2, ProcessCode.HEAT_TREAT, outsourced=True),
        )),
    ]
    result = find_spofs(orders, resources, exposed_sites={"ven_heat"})
    by_id = {item.resource_id: item for item in result.items}
    assert by_id["grinder"].exposed is False
    assert by_id["heat"].exposed is True


def test_graph_has_part_step_and_resource_nodes():
    resources = [machine("grinder", ProcessCode.GRIND_CYL, 0.005), supplier("steel", "EN24")]
    orders = [order("o1", 1.0, "EN24", (step("s1", 1, ProcessCode.GRIND_CYL, 0.005),))]
    result = find_spofs(orders, resources)
    kinds = {node.kind for node in result.nodes}
    assert kinds == {"part", "step", "machine", "supplier"}
    relations = {edge.relation for edge in result.edges}
    assert relations == {"needs", "can_serve", "needs_material"}
    assert any(edge.from_node == "step:s1" and edge.to_node == "grinder" for edge in result.edges)


def test_empty_world_is_safe():
    result = find_spofs([], [])
    assert result.items == () and result.total_orders == 0


# ---------------------------------------------------------------- (b) property


PROCESSES = [ProcessCode.TURN, ProcessCode.MILL, ProcessCode.GRIND_CYL, ProcessCode.HEAT_TREAT]
TOLERANCES = [None, 0.005, 0.02, 0.05]
MATERIALS = ["EN8", "EN24", "SS304"]


def _servers_step_bruteforce(step_req: StepRequirement, resources: list[Resource]) -> set[str]:
    """Independent re-implementation of the can_serve predicate."""
    out: set[str] = set()
    for resource in resources:
        if resource.available is False:
            continue
        if step_req.outsourced:
            if resource.kind == KIND_VENDOR and resource.process == step_req.process:
                out.add(resource.id)
        else:
            if resource.kind != KIND_MACHINE or resource.process != step_req.process:
                continue
            if step_req.tolerance_mm is not None and resource.tolerance_mm is not None:
                if resource.tolerance_mm > step_req.tolerance_mm:
                    continue
            if step_req.envelope_mm is not None and resource.envelope_mm is not None:
                if resource.envelope_mm < step_req.envelope_mm:
                    continue
            out.add(resource.id)
    return out


def _bruteforce(orders: list[OrderRequirement], resources: list[Resource]) -> dict[str, tuple[tuple[str, ...], float]]:
    """Remove each resource and re-check: the naive implementation."""
    found: dict[str, tuple[tuple[str, ...], float]] = {}
    for resource in resources:
        broken: list[str] = []
        revenue = 0.0
        for order_req in orders:
            hit = False
            for step_req in order_req.steps:
                servers = _servers_step_bruteforce(step_req, resources)
                if resource.id in servers and len(servers) == 1:
                    hit = True
            material_servers = {
                r.id for r in resources if r.kind == KIND_SUPPLIER and r.material == order_req.material
            }
            if resource.id in material_servers and len(material_servers) == 1:
                hit = True
            if hit:
                broken.append(order_req.order_id)
                revenue += order_req.value_inr
        if broken:
            found[resource.id] = (tuple(sorted(broken)), round(revenue, 2))
    return found


_resource_strategy = st.one_of(
    st.builds(
        lambda i, process, tolerance, available, envelope: Resource(
            id=f"m{i}", kind=KIND_MACHINE, name=f"m{i}", site_id="fac_owner",
            process=process, tolerance_mm=tolerance, envelope_mm=envelope, available=available,
        ),
        st.integers(min_value=0, max_value=4),
        st.sampled_from(PROCESSES),
        st.sampled_from(TOLERANCES),
        st.booleans(),
        st.one_of(st.none(), st.floats(min_value=100, max_value=800)),
    ),
    st.builds(
        lambda i, process: Resource(
            id=f"v{i}", kind=KIND_VENDOR, name=f"v{i}", site_id=f"v{i}", process=process,
        ),
        st.integers(min_value=0, max_value=2),
        st.sampled_from(PROCESSES),
    ),
    st.builds(
        lambda i, material: Resource(
            id=f"s{i}", kind=KIND_SUPPLIER, name=f"s{i}", site_id=f"s{i}", material=material,
        ),
        st.integers(min_value=0, max_value=2),
        st.sampled_from(MATERIALS),
    ),
)

_order_strategy = st.builds(
    lambda oi, value, material, steps: OrderRequirement(
        order_id=f"o{oi}", part_id=f"p{oi}", part_name=f"Part {oi}",
        value_inr=value, material=material, steps=steps,
    ),
    st.integers(min_value=0, max_value=3),
    st.floats(min_value=1, max_value=1_000_000),
    st.sampled_from(MATERIALS),
    st.lists(
        st.builds(
            lambda si, process, tolerance, outsourced: StepRequirement(
                step_id=f"st{si}", seq=si + 1, process=process,
                tolerance_mm=tolerance, outsourced=outsourced, envelope_mm=None,
            ),
            st.integers(min_value=0, max_value=3),
            st.sampled_from(PROCESSES),
            st.sampled_from(TOLERANCES),
            st.booleans(),
        ),
        min_size=1, max_size=3, unique_by=lambda s: s.step_id,
    ),
)


@settings(max_examples=200, deadline=None)
@given(resources=st.lists(_resource_strategy, max_size=8), orders=st.lists(_order_strategy, max_size=4))
def test_algorithm_matches_bruteforce(resources, orders):
    """Section 10 Phase 6 (b): the coverage algorithm == remove-and-recheck."""
    # collapse duplicate ids (strategies can generate two m0s)
    unique_resources: dict[str, Resource] = {}
    for resource in resources:
        unique_resources.setdefault(resource.id, resource)
    unique_orders: dict[str, OrderRequirement] = {}
    for order_req in orders:
        unique_orders.setdefault(order_req.order_id, order_req)
    resources_list = list(unique_resources.values())
    orders_list = list(unique_orders.values())

    result = find_spofs(orders_list, resources_list)
    actual = {item.resource_id: (item.orders_broken, item.revenue_at_risk_inr) for item in result.items}
    expected = _bruteforce(orders_list, resources_list)
    assert actual == expected


def test_property_material_servers_match_bruteforce():
    resources = [supplier("a", "EN8"), supplier("b", "EN24"), machine("m", ProcessCode.TURN)]
    order_req = order("o1", 1.0, "EN24", (step("s1", 1, ProcessCode.TURN, 0.02),))
    assert servers_for_material(order_req, resources) == {"b"}