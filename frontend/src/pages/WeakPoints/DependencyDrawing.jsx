import { useMemo } from 'react'
import { orderLabel, stepLabel } from '../../lib/status'

const columns = [
  { kind: 'order', label: 'ORDERS' },
  { kind: 'part', label: 'PARTS' },
  { kind: 'step', label: 'STEPS' },
  { kind: 'resource', label: 'RESOURCES' },
]

export function DependencyDrawing({ nodes = [], edges = [], orders = [], spofs = [], selectedResourceId, failedOrderIds = [] }) {
  const graph = useMemo(() => {
    const partNodes = nodes.filter((node) => node.kind === 'part').sort((a, b) => a.id.localeCompare(b.id))
    const stepNodes = nodes
      .filter((node) => node.kind === 'step')
      .sort((a, b) => a.id.localeCompare(b.id))
      .map((node) => ({ ...node, name: stepLabel(node.name) }))
    const resourceNodes = nodes.filter((node) => ['machine', 'vendor', 'supplier'].includes(node.kind)).sort((a, b) => a.name.localeCompare(b.name))
    const orderNodes = orders.map((order) => ({
      id: `order:${order.id}`,
      kind: 'order',
      // `orderId` keeps the raw id for matching; `name` is what a person reads.
      orderId: order.id,
      name: orderLabel(order.id),
      part_id: order.part_id,
      state: order.state,
    }))
    const lists = [orderNodes, partNodes, stepNodes, resourceNodes]
    const maxRows = Math.max(1, ...lists.map((list) => list.length))
    const height = Math.max(470, 80 + maxRows * 48)
    const x = { order: 80, part: 350, step: 630, resource: 920 }
    const positions = new Map()
    for (const column of columns) {
      const list = lists.find((items) => items[0]?.kind === column.kind) || lists[columns.indexOf(column)]
      const items = list || []
      items.forEach((node, index) => {
        positions.set(node.id, { x: x[column.kind], y: 68 + index * 48, node })
      })
    }
    const allEdges = [
      ...orders.map((order) => ({ from_node: `order:${order.id}`, to_node: `part:${order.part_id}`, relation: 'needs' })),
      ...edges,
    ]
    return { height, positions, edges: allEdges }
  }, [nodes, edges, orders])

  const spofIds = new Set(spofs.map((item) => item.resource_id))
  const failed = new Set(failedOrderIds)
  const lineIsBroken = (edge) => {
    if (!selectedResourceId) return false
    if (edge.to_node === selectedResourceId) return true
    if (edge.from_node.startsWith('step:') && edge.to_node === selectedResourceId) return true
    const from = graph.positions.get(edge.from_node)?.node
    return from?.kind === 'order' && failed.has(from.orderId)
  }

  return (
    <div className="weak-graph-scroll">
      <svg
        className="weak-graph"
        viewBox={`0 0 1080 ${graph.height}`}
        role="img"
        aria-label="Dependency drawing from orders through parts and steps to resources"
      >
        <defs>
          <pattern id="weak-hatch" width="8" height="8" patternTransform="rotate(45)" patternUnits="userSpaceOnUse">
            <rect width="8" height="8" fill="var(--c-deep)" />
            <path d="M 0 0 V 8" stroke="var(--c-sun)" strokeWidth="2" />
          </pattern>
        </defs>
        {columns.map((column) => (
          <text key={column.kind} x={graph.positions.get(`${column.kind}:`)?.x ?? ({ order: 80, part: 350, step: 630, resource: 920 }[column.kind])} y="24" className="weak-graph__column">
            {column.label}
          </text>
        ))}
        {graph.edges.map((edge, index) => {
          const from = graph.positions.get(edge.from_node)
          const to = graph.positions.get(edge.to_node)
          if (!from || !to) return null
          const broken = lineIsBroken(edge)
          return (
            <path
              key={`${edge.from_node}-${edge.to_node}-${index}`}
              d={`M ${from.x + 74} ${from.y} C ${from.x + 130} ${from.y}, ${to.x - 80} ${to.y}, ${to.x - 74} ${to.y}`}
              className={`weak-graph__edge ${broken ? 'is-broken' : ''} ${edge.relation === 'can_serve' ? 'is-alternative' : ''}`}
            />
          )
        })}
        {[...graph.positions.entries()].map(([id, point]) => {
          const { node, x, y } = point
          const isSpof = spofIds.has(id)
          const dimmed = selectedResourceId && node.kind === 'resource' && id !== selectedResourceId
          const brokenOrder = node.kind === 'order' && failed.has(node.orderId)
          return (
            <g key={id} className={`weak-graph__node weak-graph__node--${node.kind} ${isSpof ? 'is-spof' : ''} ${dimmed ? 'is-dimmed' : ''} ${brokenOrder ? 'is-broken' : ''}`}>
              <rect x={x - 74} y={y - 14} width="148" height="28" fill={brokenOrder ? 'url(#weak-hatch)' : undefined} />
              <text x={x} y={y + 4} textAnchor="middle">{node.name}</text>
              {node.process && <title>{node.process}</title>}
            </g>
          )
        })}
      </svg>
    </div>
  )
}
