"""M1 services: factories, machines, parts, orders (section 8).

Services raise AppError (never 500) and return ORM rows; routers convert to
response schemas. Runtime rows get UUID4 ids per section 5; seeded rows keep
their readable slugs.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import AppError
from app.models import Factory, Machine, Order, Part
from app.schemas.factories import FactoryCreate, FactoryUpdate, MachineCreate, MachineUpdate, OrderCreate


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def list_factories(session: Session) -> list[Factory]:
    return list(session.scalars(select(Factory).order_by(Factory.id)))


def get_factory(session: Session, factory_id: str) -> Factory:
    factory = session.get(Factory, factory_id)
    if factory is None:
        raise AppError("NOT_FOUND", f"Factory {factory_id!r} does not exist.", status_code=404)
    return factory


def create_factory(session: Session, payload: FactoryCreate) -> Factory:
    factory = Factory(
        id=_new_id("fac"),
        role=payload.role,
        name=payload.name,
        lat=payload.lat,
        lon=payload.lon,
        cluster_id=payload.cluster_id,
        hazard_zone_id=payload.hazard_zone_id,
        grid_id=payload.grid_id,
        shift_hours_per_day=payload.shift_hours_per_day,
        materials_handled=payload.materials_handled,
        typical_lead_time_hours=payload.typical_lead_time_hours,
        mobilisation_hours=payload.mobilisation_hours,
        spare_hours_per_week=payload.spare_hours_per_week,
        contacts=payload.contacts,
    )
    session.add(factory)
    session.commit()
    return factory


def update_factory(session: Session, factory_id: str, payload: FactoryUpdate) -> Factory:
    factory = get_factory(session, factory_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(factory, field, value)
    session.commit()
    return factory


def create_machines(session: Session, factory_id: str, payload: MachineCreate) -> list[Machine]:
    get_factory(session, factory_id)  # 404 when unknown
    machines = [
        Machine(
            id=_new_id("mch"),
            factory_id=factory_id,
            process=payload.process,
            name=payload.name,
            achievable_tolerance_mm=payload.achievable_tolerance_mm,
            envelope_mm=payload.envelope_mm,
            available=payload.available,
        )
        for _ in range(payload.count)
    ]
    session.add_all(machines)
    session.commit()
    return machines


def list_machines(session: Session, factory_id: str) -> list[Machine]:
    get_factory(session, factory_id)
    return list(session.scalars(select(Machine).where(Machine.factory_id == factory_id).order_by(Machine.id)))


def update_machine(session: Session, machine_id: str, payload: MachineUpdate) -> Machine:
    machine = session.get(Machine, machine_id)
    if machine is None:
        raise AppError("NOT_FOUND", f"Machine {machine_id!r} does not exist.", status_code=404)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(machine, field, value)
    session.commit()
    return machine


def delete_machine(session: Session, machine_id: str) -> None:
    machine = session.get(Machine, machine_id)
    if machine is None:
        raise AppError("NOT_FOUND", f"Machine {machine_id!r} does not exist.", status_code=404)
    session.delete(machine)
    session.commit()


def list_parts(session: Session, factory_id: str) -> list[Part]:
    get_factory(session, factory_id)
    return list(session.scalars(select(Part).where(Part.factory_id == factory_id).order_by(Part.id)))


def create_order(session: Session, factory_id: str, payload: OrderCreate) -> Order:
    get_factory(session, factory_id)
    part = session.get(Part, payload.part_id)
    if part is None:
        raise AppError(
            "NOT_FOUND",
            f"Part {payload.part_id!r} does not exist.",
            status_code=404,
            details={"part_id": payload.part_id},
        )
    if part.factory_id != factory_id:
        raise AppError(
            "PART_NOT_IN_FACTORY",
            f"Part {payload.part_id!r} belongs to factory {part.factory_id!r}, not {factory_id!r}.",
            status_code=409,
        )
    order = Order(
        id=_new_id("ord"),
        factory_id=factory_id,
        part_id=payload.part_id,
        qty=payload.qty,
        due_at=payload.due_at,
        value_inr=payload.value_inr,
        customer_alias=payload.customer_alias,
    )
    session.add(order)
    session.commit()
    return order


def list_orders(session: Session, factory_id: str) -> list[Order]:
    get_factory(session, factory_id)
    return list(session.scalars(select(Order).where(Order.factory_id == factory_id).order_by(Order.id)))
