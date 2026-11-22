"""M3 router: ranked single points of failure plus the dependency graph (section 8)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.spof import SpofEdge, SpofItem, SpofNode, SpofOut
from app.services import spof as service

router = APIRouter(tags=["spof"])


@router.get(
    "/factories/{factory_id}/spof",
    response_model=SpofOut,
    summary="Rank single points of failure and dependency graph",
)
def get_spof(factory_id: str, session: Session = Depends(get_db)):
    result, trace = service.compute_spof(session, factory_id)
    return SpofOut(
        factory_id=factory_id,
        items=[
            SpofItem(
                rank=item.rank,
                resource_id=item.resource_id,
                kind=item.kind,
                name=item.name,
                orders_broken=list(item.orders_broken),
                steps_broken=list(item.steps_broken),
                revenue_at_risk_inr=item.revenue_at_risk_inr,
                exposed=item.exposed,
            )
            for item in result.items
        ],
        nodes=[
            SpofNode(id=node.id, kind=node.kind, name=node.name, process=node.process, exposed=node.exposed)
            for node in result.nodes
        ],
        edges=[
            SpofEdge(from_node=edge.from_node, to_node=edge.to_node, relation=edge.relation)
            for edge in result.edges
        ],
        uncovered_requirements=list(result.uncovered_requirements),
        total_orders=result.total_orders,
        trace=trace,
    )
