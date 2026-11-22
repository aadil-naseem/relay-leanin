"""M1 routers: factories, machines, parts, orders (section 8)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.factories import (
    FactoryCreate,
    FactoryListOut,
    FactoryOut,
    FactoryUpdate,
    MachineCreate,
    MachineListOut,
    MachineOut,
    MachineUpdate,
    OrderCreate,
    OrderListOut,
    OrderOut,
    PartListOut,
    PartOut,
)
from app.services import factories as service

router = APIRouter(tags=["factories"])


@router.get("/factories", response_model=FactoryListOut, summary="List sample and configured factories")
def get_factories(session: Session = Depends(get_db)):
    return {"items": [FactoryOut.model_validate(f) for f in service.list_factories(session)]}


@router.post("/factories", response_model=FactoryOut, status_code=201, summary="Create a factory")
def post_factory(payload: FactoryCreate, session: Session = Depends(get_db)):
    return FactoryOut.model_validate(service.create_factory(session, payload))


@router.get("/factories/{factory_id}", response_model=FactoryOut, summary="Read a factory")
def get_factory(factory_id: str, session: Session = Depends(get_db)):
    return FactoryOut.model_validate(service.get_factory(session, factory_id))


@router.put("/factories/{factory_id}", response_model=FactoryOut)
def put_factory(factory_id: str, payload: FactoryUpdate, session: Session = Depends(get_db)):
    return FactoryOut.model_validate(service.update_factory(session, factory_id, payload))


@router.post("/factories/{factory_id}/machines", response_model=list[MachineOut], status_code=201)
def post_machines(factory_id: str, payload: MachineCreate, session: Session = Depends(get_db)):
    machines = service.create_machines(session, factory_id, payload)
    return [MachineOut.model_validate(m) for m in machines]


@router.get("/factories/{factory_id}/machines", response_model=MachineListOut)
def get_machines(factory_id: str, session: Session = Depends(get_db)):
    return {"items": [MachineOut.model_validate(m) for m in service.list_machines(session, factory_id)]}


@router.put("/machines/{machine_id}", response_model=MachineOut)
def put_machine(machine_id: str, payload: MachineUpdate, session: Session = Depends(get_db)):
    return MachineOut.model_validate(service.update_machine(session, machine_id, payload))


@router.delete("/machines/{machine_id}", status_code=204)
def delete_machine(machine_id: str, session: Session = Depends(get_db)):
    service.delete_machine(session, machine_id)


@router.get("/factories/{factory_id}/parts", response_model=PartListOut)
def get_parts(factory_id: str, session: Session = Depends(get_db)):
    return {"items": [PartOut.model_validate(p) for p in service.list_parts(session, factory_id)]}


@router.post("/factories/{factory_id}/orders", response_model=OrderOut, status_code=201)
def post_order(factory_id: str, payload: OrderCreate, session: Session = Depends(get_db)):
    return OrderOut.model_validate(service.create_order(session, factory_id, payload))


@router.get("/factories/{factory_id}/orders", response_model=OrderListOut)
def get_orders(
    factory_id: str,
    session: Session = Depends(get_db),
    part_id: str | None = Query(default=None),
):
    orders = service.list_orders(session, factory_id)
    if part_id is not None:
        orders = [order for order in orders if order.part_id == part_id]
    return {"items": [OrderOut.model_validate(o) for o in orders]}
