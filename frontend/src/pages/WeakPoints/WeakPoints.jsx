import { useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useFactoryOrders, useSpof } from '../../api/hooks/useSpof'
import { CalcLog, Money } from '../../components/domain'
import { orderLabel } from '../../lib/status'
import { Button, Frame, Nameplate, Skeleton, Toast } from '../../components/primitives'
import { useRelayNavigate } from '../../app/navigation'
import { DependencyDrawing } from './DependencyDrawing'

export default function WeakPoints() {
  const navigate = useRelayNavigate()
  const [searchParams] = useSearchParams()
  const spof = useSpof()
  const orders = useFactoryOrders()
  const [selectedId, setSelectedId] = useState(searchParams.get('resource') || null)
  const [simulatedId, setSimulatedId] = useState(null)
  const [traceOpen, setTraceOpen] = useState(false)

  const selected = spof.data?.items.find((item) => item.resource_id === selectedId) || spof.data?.items[0]
  const brokenOrders = useMemo(() => {
    const orderIds = new Set(selected?.orders_broken || [])
    return (orders.data?.items || []).filter((order) => orderIds.has(order.id))
  }, [orders.data, selected])
  const simulatedItem = simulatedId ? spof.data?.items.find((item) => item.resource_id === simulatedId) : null
  const simulatedOrders = useMemo(() => {
    const orderIds = new Set(simulatedItem?.orders_broken || [])
    return (orders.data?.items || []).filter((order) => orderIds.has(order.id))
  }, [orders.data, simulatedItem])

  if (spof.isLoading || orders.isLoading) {
    return <main className="weak-page"><div className="f0-kicker">DEPENDENCY ANALYSIS</div><h1>WEAK POINTS</h1><Skeleton lines={6} /></main>
  }

  if (spof.isError || orders.isError) {
    const error = spof.error || orders.error
    return (
      <main className="weak-page">
        <div className="f0-kicker">DEPENDENCY ANALYSIS</div><h1>WEAK POINTS</h1>
        <Frame className="weak-error">
          <Nameplate>{error.code || 'CONNECTION_ERROR'}</Nameplate>
          <p>{error.message}</p>
          <Button variant="secondary" onClick={() => { spof.refetch(); orders.refetch() }}>Retry</Button>
        </Frame>
      </main>
    )
  }

  const activeSimulation = simulatedItem
  const failedIds = activeSimulation?.orders_broken || []
  const resetSimulation = () => setSimulatedId(null)

  return (
    <main className="weak-page">
      <header className="weak-heading">
        <div><span className="f0-kicker">DEPENDENCY ANALYSIS · {spof.data.total_orders} ACTIVE ORDERS</span><h1>WEAK POINTS</h1></div>
        <Button variant="ghost" onClick={() => setTraceOpen(true)}>How was this calculated?</Button>
      </header>

      <section className="weak-layout">
        <Frame className="weak-list">
          <div className="weak-list__heading"><span className="f0-kicker">RANKED SINGLE POINTS OF FAILURE</span></div>
          {spof.data.items.length ? (
            <ol>
              {spof.data.items.map((item) => (
                <li key={item.resource_id}>
                  <button
                    type="button"
                    className={selected?.resource_id === item.resource_id ? 'is-selected' : ''}
                    aria-pressed={selected?.resource_id === item.resource_id}
                    onClick={() => setSelectedId(item.resource_id)}
                  >
                    <span className="weak-rank">{item.rank}</span>
                    <span className="weak-list__main">
                      <strong>{item.name}</strong>
                      <small>{item.orders_broken.length} order{item.orders_broken.length === 1 ? '' : 's'} · {item.kind}</small>
                    </span>
                    <Money value={item.revenue_at_risk_inr} />
                    {item.exposed && <i className="weak-exposed" title="Inside a curated hazard zone" />}
                  </button>
                </li>
              ))}
            </ol>
          ) : (
            <p>No single points of failure found in the current order set.</p>
          )}
          <p className="weak-list__footnote">Three lathes never appear here: losing one still leaves two.</p>
        </Frame>

        <Frame className="weak-drawing">
          <header className="weak-drawing__header">
            <div><span className="f0-kicker">ORDER → PART → STEP → RESOURCE</span><h2>Dependency drawing</h2></div>
            <div className="weak-legend">
              <span><i className="weak-legend__spof" />SPOF</span>
              <span><i className="weak-legend__alt" />Alternative</span>
            </div>
          </header>
          {activeSimulation && (
            <Toast tone="warning" onDismiss={resetSimulation}>
              PULL THE PLUG · {activeSimulation.name} · {simulatedOrders.length} order(s) break
            </Toast>
          )}
          <DependencyDrawing
            nodes={spof.data.nodes}
            edges={spof.data.edges}
            orders={orders.data.items}
            spofs={spof.data.items}
            selectedResourceId={simulatedId}
            failedOrderIds={failedIds}
          />
          {selected && (
            <footer className="weak-drawing__footer">
              <div className="weak-selection">
                <Nameplate>{selected.resource_id}</Nameplate>
                <span>{selected.name}</span>
                <span>{selected.orders_broken.length} order(s) · <Money value={selected.revenue_at_risk_inr} /></span>
              </div>
              <div className="weak-actions">
                <Button
                  variant={simulatedId === selected.resource_id ? 'ghost' : 'secondary'}
                  onClick={() => setSimulatedId(simulatedId === selected.resource_id ? null : selected.resource_id)}
                >
                  {simulatedId === selected.resource_id ? 'Reset loss' : 'Simulate loss'}
                </Button>
                <Button variant="primary" onClick={() => navigate(`/app/what-if?hazard=RESOURCE_DOWN&resource_id=${encodeURIComponent(selected.resource_id)}`)}>
                  Stress this resource →
                </Button>
              </div>
            </footer>
          )}
          {selected && (
            <div className="weak-broken-orders">
              <span className="f0-kicker">{simulatedId ? 'BREAKS' : 'ORDERS AT RISK IF LOST'}</span>
              <div>{(simulatedId ? simulatedOrders : brokenOrders).length
                ? (simulatedId ? simulatedOrders : brokenOrders).map((order) => (
                  <Nameplate key={order.id}>{orderLabel(order.id)} · {order.customer_alias || 'Sample order'}</Nameplate>
                ))
                : <span>No active orders depend on this resource.</span>}</div>
            </div>
          )}
        </Frame>

        {!!spof.data.uncovered_requirements?.length && (
          <Frame className="weak-uncovered">
            <span className="f0-kicker">COVERAGE GAPS</span>
            <p>Requirements with no approved server at baseline are listed separately; they are not attributed to every resource.</p>
            <ul>{spof.data.uncovered_requirements.slice(0, 5).map((item) => <li key={item}>{item}</li>)}</ul>
          </Frame>
        )}
      </section>

      <CalcDrawer open={traceOpen} onClose={() => setTraceOpen(false)} trace={spof.data.trace || []} />
    </main>
  )
}

function CalcDrawer({ open, onClose, trace }) {
  if (!open) return null
  return (
    <div className="desk-overlay" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section className="desk-breakdown desk-breakdown--calc" role="dialog" aria-modal="true" aria-label="SPOF calculation log">
        <header><div><span className="f0-kicker">CALCULATION LOG</span><h2>How was this calculated?</h2></div><Button variant="ghost" size="small" onClick={onClose}>Close</Button></header>
        <CalcLog entries={trace} />
      </section>
    </div>
  )
}
