"""M3 single-point-of-failure finder (blueprint section 7.1). Pure logic.

Graph model: Order -> Part -> Step(process) -> Resource, plus Part -> material
-> Supplier. A resource is an in-house machine, an approved vendor (outsourced
steps) or an approved supplier (material).

Algorithm (coverage-based, exactly section 7.1):
  1. For each active order, list its requirements: every step plus its material.
  2. For each requirement, compute servers(req) = set of resources that can serve it.
  3. For each resource: remove it; an order is BROKEN if any requirement that had
     servers at baseline now has an empty server set.
  4. A resource is a SPOF when it breaks at least one order.
  5. Rank by revenue at risk desc, then order count.

Two modelling decisions, recorded in docs/PROGRESS.md:

* **Baseline-uncovered requirements do not count against resources.** A part
  with no approved supplier is "uncovered" on its own; blaming every resource for
  it would make the ranking meaningless. They are returned separately in
  `uncovered_requirements` so the UI can say "PRT-B has no approved EN8 supplier"
  instead of silently pretending it is covered.
* **Step ownership by `outsourced`.** An outsourced step is served by approved
  vendors (a vendor process), an in-house step by the factory's own machines.
  Machines are individual rows, so 3 lathes never form a SPOF (section 7.1).

No database or FastAPI imports: the service layer builds the views below.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.enums import ProcessCode

KIND_MACHINE = "machine"
KIND_VENDOR = "vendor"
KIND_SUPPLIER = "supplier"


@dataclass(frozen=True)
class Resource:
    """One thing that can be removed: a machine, a vendor or a supplier."""

    id: str
    kind: str  # machine | vendor | supplier
    name: str
    site_id: str  # owning factory (machines) or the vendor/supplier site
    process: ProcessCode | None = None  # machines + vendors
    material: str | None = None  # suppliers
    tolerance_mm: float | None = None  # machines: achievable tolerance (smaller is better)
    envelope_mm: float | None = None  # machines: largest dimension accepted
    available: bool = True


@dataclass(frozen=True)
class StepRequirement:
    step_id: str
    seq: int
    process: ProcessCode
    tolerance_mm: float | None = None  # tightest tolerance this step must hold
    outsourced: bool = False
    envelope_mm: float | None = None  # part envelope, from the passport when known


@dataclass(frozen=True)
class OrderRequirement:
    """One active order: its value, material and route."""

    order_id: str
    part_id: str
    part_name: str
    value_inr: float
    material: str
    steps: tuple[StepRequirement, ...] = ()

    @property
    def label(self) -> str:
        return f"{self.order_id} ({self.part_name})"


@dataclass(frozen=True)
class SpofItem:
    rank: int
    resource_id: str
    kind: str
    name: str
    orders_broken: tuple[str, ...]
    steps_broken: tuple[str, ...]
    revenue_at_risk_inr: float
    exposed: bool = False


@dataclass(frozen=True)
class GraphNode:
    id: str
    kind: str  # part | step | machine | vendor | supplier
    name: str
    process: ProcessCode | None = None
    exposed: bool = False


@dataclass(frozen=True)
class GraphEdge:
    from_node: str
    to_node: str
    relation: str  # needs | can_serve | needs_material


@dataclass(frozen=True)
class SpofResult:
    items: tuple[SpofItem, ...] = ()
    nodes: tuple[GraphNode, ...] = ()
    edges: tuple[GraphEdge, ...] = ()
    uncovered_requirements: tuple[str, ...] = ()
    excluded_resources: tuple[str, ...] = ()  # unavailable machines/vendors, for the trace
    total_orders: int = 0


def machine_can_serve(step: StepRequirement, machine: Resource) -> bool:
    """Machine process matches, tolerance holds, envelope fits (section 7.1)."""
    if machine.kind != KIND_MACHINE or not machine.available:
        return False
    if step.outsourced:
        return False  # outsourced work goes to a vendor, not the shop floor
    if machine.process != step.process:
        return False
    if step.tolerance_mm is not None and machine.tolerance_mm is not None:
        if machine.tolerance_mm > step.tolerance_mm:
            return False  # cannot hold the tolerance the drawing demands
    if step.envelope_mm is not None and machine.envelope_mm is not None:
        if machine.envelope_mm < step.envelope_mm:
            return False  # part will not fit the machine
    return True


def vendor_can_serve(step: StepRequirement, vendor: Resource) -> bool:
    if vendor.kind != KIND_VENDOR or not vendor.available:
        return False
    if not step.outsourced:
        return False  # in-house work is not handed to a vendor in this model
    return vendor.process == step.process


def supplier_can_serve(order: OrderRequirement, supplier: Resource) -> bool:
    if supplier.kind != KIND_SUPPLIER:
        return False
    return supplier.material is not None and supplier.material == order.material


def servers_for_step(step: StepRequirement, resources: list[Resource]) -> frozenset[str]:
    return frozenset(
        resource.id
        for resource in resources
        if machine_can_serve(step, resource) or vendor_can_serve(step, resource)
    )


def servers_for_material(order: OrderRequirement, resources: list[Resource]) -> frozenset[str]:
    return frozenset(resource.id for resource in resources if supplier_can_serve(order, resource))


def _requirements(order: OrderRequirement, resources: list[Resource]) -> list[tuple[str, str, str, frozenset[str]]]:
    """(requirement_key, step_id_or_empty, label, servers) for one order."""
    rows: list[tuple[str, str, str, frozenset[str]]] = []
    for step in order.steps:
        servers = servers_for_step(step, resources)
        rows.append((f"{order.order_id}:{step.step_id}", step.step_id, f"step {step.seq} {step.process.value}", servers))
    material_servers = servers_for_material(order, resources)
    rows.append((f"{order.order_id}:material", "", f"material {order.material}", material_servers))
    return rows


def find_spofs(
    orders: list[OrderRequirement],
    resources: list[Resource],
    exposed_sites: set[str] | None = None,
) -> SpofResult:
    """Ranked SPOF list plus the dependency graph (section 7.1)."""
    exposed = exposed_sites or set()
    resource_by_id = {resource.id: resource for resource in resources}

    # --- 1-2. requirements and their baseline server sets ---
    requirement_rows: list[tuple[OrderRequirement, list[tuple[str, str, str, frozenset[str]]]]] = []
    uncovered: list[str] = []
    for order in orders:
        rows = _requirements(order, resources)
        requirement_rows.append((order, rows))
        for key, _step_id, label, servers in rows:
            if not servers:
                uncovered.append(f"{order.label}: {label} has no approved server")

    # --- 3. remove each resource, re-check coverage ---
    items: list[SpofItem] = []
    for resource_id in sorted(resource_by_id):
        broken_orders: list[str] = []
        broken_steps: set[str] = set()
        revenue = 0.0
        for order, rows in requirement_rows:
            order_broken = False
            for _key, step_id, _label, servers in rows:
                if not servers:
                    continue  # uncovered at baseline: not this resource's fault
                if resource_id in servers and len(servers) == 1:
                    order_broken = True
                    if step_id:
                        broken_steps.add(step_id)
            if order_broken:
                broken_orders.append(order.order_id)
                revenue += order.value_inr
        if not broken_orders:
            continue
        resource = resource_by_id[resource_id]
        items.append(
            SpofItem(
                rank=0,  # assigned after sorting
                resource_id=resource.id,
                kind=resource.kind,
                name=resource.name,
                orders_broken=tuple(sorted(broken_orders)),
                steps_broken=tuple(sorted(broken_steps)),
                revenue_at_risk_inr=round(revenue, 2),
                exposed=resource.site_id in exposed,
            )
        )

    # --- 5. rank: revenue desc, then order count, then id for determinism ---
    items.sort(key=lambda item: (-item.revenue_at_risk_inr, -len(item.orders_broken), item.resource_id))
    ranked = tuple(
        SpofItem(
            rank=index + 1,
            resource_id=item.resource_id,
            kind=item.kind,
            name=item.name,
            orders_broken=item.orders_broken,
            steps_broken=item.steps_broken,
            revenue_at_risk_inr=item.revenue_at_risk_inr,
            exposed=item.exposed,
        )
        for index, item in enumerate(items)
    )

    # --- 6. dependency graph for the UI ---
    nodes: dict[str, GraphNode] = {}
    edges: set[GraphEdge] = set()
    for order in orders:
        part_node = f"part:{order.part_id}"
        nodes.setdefault(part_node, GraphNode(id=part_node, kind="part", name=order.part_name))
        for step in order.steps:
            step_node = f"step:{step.step_id}"
            nodes.setdefault(
                step_node,
                GraphNode(id=step_node, kind="step", name=f"{step.process.value} (seq {step.seq})", process=step.process),
            )
            edges.add(GraphEdge(from_node=part_node, to_node=step_node, relation="needs"))
            for server_id in servers_for_step(step, resources):
                edges.add(GraphEdge(from_node=step_node, to_node=server_id, relation="can_serve"))
        for supplier_id in servers_for_material(order, resources):
            edges.add(GraphEdge(from_node=part_node, to_node=supplier_id, relation="needs_material"))

    for resource in resources:
        nodes.setdefault(
            resource.id,
            GraphNode(
                id=resource.id,
                kind=resource.kind,
                name=resource.name,
                process=resource.process,
                exposed=resource.site_id in exposed,
            ),
        )

    excluded = tuple(sorted(r.id for r in resources if not r.available))
    return SpofResult(
        items=ranked,
        nodes=tuple(sorted(nodes.values(), key=lambda node: node.id)),
        edges=tuple(sorted(edges, key=lambda edge: (edge.from_node, edge.to_node, edge.relation))),
        uncovered_requirements=tuple(uncovered),
        excluded_resources=excluded,
        total_orders=len(orders),
    )