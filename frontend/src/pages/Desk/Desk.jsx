import { lazy, Suspense, useEffect, useMemo, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { apiRequest } from '../../api/client'
import { useDashboard, useExposureMap, useOwnerExposure, useReadiness, useReadinessActions, useStressTest } from '../../api/hooks/useDeskData'
import { AlertBanner, CalcLog, DimensionLine, Money, Odometer, ReadinessRing, RiskPill } from '../../components/domain'
import { Button, Frame, Nameplate, Segmented, Skeleton, Toast } from '../../components/primitives'
import { readinessReasonLabel } from '../../lib/status'
import { useRelayNavigate } from '../../app/navigation'
import { useUiStore } from '../../store/ui'

const ExposureMiniMap = lazy(() => import('./ExposureMiniMap').then((module) => ({ default: module.ExposureMiniMap })))

const windows = [24, 48, 72]

export default function Desk() {
  const navigate = useRelayNavigate()
  const snapshotMode = useUiStore((state) => state.snapshotMode)
  const queryClient = useQueryClient()
  const dashboard = useDashboard()
  const map = useExposureMap()
  const readiness = useReadiness()
  const actions = useReadinessActions()
  const exposure = useOwnerExposure()
  const stressId = dashboard.data?.alert?.stress_test_id
  const stress = useStressTest(stressId)
  const [windowHours, setWindowHours] = useState(48)
  const [breakdownOpen, setBreakdownOpen] = useState(false)
  const [calcLogOpen, setCalcLogOpen] = useState(false)
  const [coldOpen, setColdOpen] = useState(false)

  useEffect(() => {
    let frame
    try {
      const alreadyPlayed = sessionStorage.getItem('relay-desk-opened') === 'true'
      frame = window.requestAnimationFrame(() => setColdOpen(!alreadyPlayed))
      if (!alreadyPlayed) sessionStorage.setItem('relay-desk-opened', 'true')
    } catch {
      frame = window.requestAnimationFrame(() => setColdOpen(false))
    }
    return () => window.cancelAnimationFrame(frame)
  }, [])

  const makeRecovery = useMutation({
    mutationFn: ({ stress_test_id, order_id }) => apiRequest('/recovery-requests', {
      method: 'POST',
      body: JSON.stringify({ from_stress_test_id: stress_test_id, order_id }),
    }),
    onSuccess: async (request) => {
      useUiStore.getState().setPreference('presenterRecoveryId', request.id)
      await queryClient.invalidateQueries({ queryKey: ['recovery-request', request.id] })
      navigate(`/app/recovery/${request.id}`)
    },
  })

  const worstOrder = useMemo(() => {
    const orders = stress.data?.orders || []
    const atRisk = orders.filter((order) => ['LATE', 'AT_RISK'].includes(order.state))
    return [...(atRisk.length ? atRisk : orders)].sort((a, b) => b.value_inr - a.value_inr)[0]
  }, [stress.data])

  const selectedWindow = readiness.data?.windows?.find((item) => item.window_hours === windowHours)
    || readiness.data?.windows?.find((item) => item.window_hours === 48)
  const weighted = selectedWindow?.weighted_score ?? dashboard.data?.readiness?.windows?.[String(windowHours)] ?? 0
  const score = selectedWindow?.score ?? (windowHours === dashboard.data?.readiness?.headline?.window
    ? dashboard.data?.readiness?.headline?.score ?? 0
    : weighted)
  const summary = stress.data?.summary

  if (dashboard.isLoading) {
    return <DeskLoading />
  }

  if (dashboard.isError) {
    return (
      <main className="desk-page">
        <Frame className="desk-error">
          <span className="f0-kicker">DESK · BACKEND UNAVAILABLE</span>
          <h1>CAN’T REACH THE SERVER</h1>
          <p>{dashboard.error?.message || 'The dashboard could not be loaded.'}</p>
          <Nameplate>{dashboard.error?.code || 'CONNECTION_ERROR'}</Nameplate>
          <Button onClick={() => dashboard.refetch()}>Retry</Button>
        </Frame>
      </main>
    )
  }

  const data = dashboard.data
  const openRecovery = () => {
    if (!data.alert.stress_test_id || !worstOrder) return
    makeRecovery.mutate({ stress_test_id: data.alert.stress_test_id, order_id: worstOrder.order_id })
  }

  return (
    <main className={`desk-page ${coldOpen ? 'desk-page--cold-open' : ''}`}>
      <header className="desk-page__heading">
        <div>
          <span className="f0-kicker">CONTROL ROOM · {data.factory.cluster_id}</span>
          <h1>DESK</h1>
        </div>
        <div className="desk-page__heading-meta">
          <RiskPill value={data.exposure_summary.owner_risk_level} />
          <Nameplate>{data.factory.name}</Nameplate>
        </div>
      </header>

      {data.weather.degraded && (
        <Toast tone="warning">
          Degraded weather feed · showing {data.weather.source} data, not a live forecast.
        </Toast>
      )}

      {data.alert.active ? (
        <AlertBanner
          level={data.exposure_summary.owner_risk_level}
          headline={data.alert.headline}
          onset={data.alert.onset_in_hours}
          action={makeRecovery.isPending ? 'Starting…' : stress.isLoading ? 'Loading at-risk orders…' : 'Start recovery request'}
          onAction={openRecovery}
          disabled={snapshotMode || makeRecovery.isPending || stress.isLoading || !worstOrder}
        />
      ) : (
        <Frame className="desk-calm">
          <span className="desk-calm__lamp" aria-hidden="true" />
          <p>No heavy rain forecast in the next 72 h. Readiness is the main job today.</p>
        </Frame>
      )}
      {makeRecovery.isError && <p className="desk-inline-error" role="alert">{makeRecovery.error.message}</p>}
      {data.alert.active && data.alert.stress_test_id && (
        <div className="desk-banner-actions">
          <Button variant="ghost" onClick={() => navigate(`/app/what-if/${data.alert.stress_test_id}`)}>See the test</Button>
        </div>
      )}

      <div className="desk-grid">
        <div className="desk-column desk-column--left">
          <Frame className="desk-readiness">
            <div className="desk-panel__heading">
              <div><span className="f0-kicker">COVERAGE</span><h2>Readiness</h2></div>
              <Segmented label="Readiness window" value={windowHours} onChange={setWindowHours} options={windows} />
            </div>
            {readiness.isError ? (
              <InlineError message={readiness.error.message} onRetry={() => readiness.refetch()} />
            ) : readiness.isLoading ? <Skeleton lines={3} /> : (
              <button className="desk-readiness__button" type="button" onClick={() => setBreakdownOpen(true)}>
                <ReadinessRing score={score} weighted={weighted} size={160} />
                <span className="desk-readiness__hint">OPEN PART-BY-PART BREAKDOWN</span>
              </button>
            )}
          </Frame>

          <Frame className="desk-weak-points">
            <div className="desk-panel__heading">
              <div><span className="f0-kicker">DEPENDENCY GRAPH</span><h2>Weak points</h2></div>
              <button className="desk-text-link" type="button" onClick={() => navigate('/app/weak-points')}>ALL →</button>
            </div>
            {data.spof_top.length ? (
              <ol>
                {data.spof_top.map((item) => (
                  <li key={item.resource_id}>
                    <button type="button" onClick={() => navigate(`/app/weak-points?resource=${encodeURIComponent(item.resource_id)}`)}>
                      <span className="desk-rank">{item.rank}</span>
                      <span className="desk-weak-points__resource">
                        <strong>{item.name}</strong>
                        <small>{item.orders_broken.length} order{item.orders_broken.length === 1 ? '' : 's'} · {item.kind}</small>
                      </span>
                      <Money value={item.revenue_at_risk_inr} />
                      {item.exposed && <i className="desk-exposed-dot" title="Exposed site" />}
                    </button>
                  </li>
                ))}
              </ol>
            ) : <p>No single points of failure found.</p>}
          </Frame>
        </div>

        <div className="desk-column desk-column--middle">
          <Frame className="desk-kpis">
            <div className="desk-panel__heading">
              <div><span className="f0-kicker">AUTO TEST · {data.alert.active ? 'FROM ALERT' : 'NO ACTIVE ALERT'}</span><h2>Exposure at a glance</h2></div>
            </div>
            {stress.isLoading && data.alert.stress_test_id ? <Skeleton lines={3} /> : (
              <div className="desk-kpis__grid">
                <Kpi label="Revenue exposed" value={summary?.revenue_exposed_inr} money />
                <Kpi label="Orders at risk" value={summary?.orders_at_risk} />
                <Kpi label="No fallback" value={summary?.orders_no_fallback} />
                <Kpi label="Stale partners" value={data.stale_partners} />
              </div>
            )}
            {stress.isError && <InlineError message={stress.error.message} onRetry={() => stress.refetch()} />}
          </Frame>

          <Frame className="desk-rain">
            <div className="desk-panel__heading">
              <div><span className="f0-kicker">72-HOUR HORIZON</span><h2>Rain outlook</h2></div>
              <WeatherPill mode={data.weather.mode} source={data.weather.source} degraded={data.weather.degraded} />
            </div>
            <div className="desk-rain__readout">
              <DimensionLine value={`${Math.round(data.exposure_summary.owner_max24_mm)} mm`} label="heaviest 24 h" />
              <span>Onset <b>T+{data.exposure_summary.owner_onset_in_hours ?? '—'}h</b></span>
            </div>
            <p className="desk-muted">Hourly rain samples are not in the current API response. This is the heaviest 24-hour window, not a time-series chart.</p>
            <button className="desk-text-link" type="button" onClick={() => navigate('/app/exposure')}>OPEN EXPOSURE →</button>
            <div className="desk-calc-trigger">
              <Button variant="ghost" size="small" onClick={() => setCalcLogOpen(true)}>How was this calculated?</Button>
            </div>
          </Frame>
        </div>

        <div className="desk-column desk-column--right">
          <Frame className="desk-actions">
            <div className="desk-panel__heading"><div><span className="f0-kicker">NEXT BEST ACTIONS</span><h2>Close the gap</h2></div></div>
            {actions.isLoading ? <Skeleton lines={3} /> : actions.isError ? (
              <InlineError message={actions.error.message} onRetry={() => actions.refetch()} />
            ) : actions.data?.actions?.length ? (
              <ol>
                {actions.data.actions.slice(0, 3).map((action) => (
                  <li key={action.relationship_id}>
                    <button type="button" onClick={() => navigate('/app/partners')}>
                      <span>{action.label}</span><b>+{action.uplift_points} pts</b>
                    </button>
                  </li>
                ))}
              </ol>
            ) : <p>No positive-uplift actions at this window.</p>}
          </Frame>

          {map.isLoading ? <Frame className="desk-map"><Skeleton lines={5} /></Frame>
            : map.isError ? <Frame className="desk-map"><InlineError message={map.error.message} onRetry={() => map.refetch()} /></Frame>
              : <Suspense fallback={<div className="desk-map__loading">Loading map layer…</div>}>
                <ExposureMiniMap points={map.data?.points || []} routes={data.exposure_summary.routes || []} />
              </Suspense>}
        </div>
      </div>

      {readiness.data && (
        <BreakdownDrawer
          open={breakdownOpen}
          onClose={() => setBreakdownOpen(false)}
          items={readiness.data.breakdown}
        />
      )}
      <CalcDrawer open={calcLogOpen} onClose={() => setCalcLogOpen(false)} entries={exposure.data?.trace || []} />
    </main>
  )
}

function Kpi({ label, value, money = false }) {
  const number = value == null ? null : Number(value)
  return (
    <div className="desk-kpi">
      <span>{label}</span>
      {number == null ? <b className="desk-kpi__empty">—</b>
        : money ? <Money value={number} />
          : <Odometer value={number} />}
    </div>
  )
}

function WeatherPill({ mode, source, degraded }) {
  return <span className={`desk-weather desk-weather--${source}`}>{source.toUpperCase()}{degraded ? ' · DEGRADED' : ''}<small>{mode}</small></span>
}

function InlineError({ message, onRetry }) {
  return (
    <div className="desk-inline-error" role="alert">
      <p>{message || 'Could not load this panel.'}</p>
      <Button variant="ghost" size="small" onClick={onRetry}>Retry</Button>
    </div>
  )
}

function DeskLoading() {
  return (
    <main className="desk-page">
      <div className="f0-kicker">CONTROL ROOM</div>
      <h1>DESK</h1>
      <Skeleton lines={4} />
    </main>
  )
}

function BreakdownDrawer({ open, onClose, items }) {
  if (!open) return null
  return (
    <div className="desk-overlay" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section className="desk-breakdown" role="dialog" aria-modal="true" aria-label="Readiness breakdown">
        <header><div><span className="f0-kicker">PART-BY-PART COVERAGE</span><h2>Readiness breakdown</h2></div><Button variant="ghost" size="small" onClick={onClose}>Close</Button></header>
        <ul>{items.map((item) => (
          <li key={item.part_id}>
            <div><strong>{item.part_name}</strong><small>{item.reason || item.detail}</small></div>
            <span>{item.covered ? `Covered by ${item.covered_by}` : readinessReasonLabel(item.reason)}</span>
          </li>
        ))}</ul>
      </section>
    </div>
  )
}

function CalcDrawer({ open, onClose, entries }) {
  if (!open) return null
  return (
    <div className="desk-overlay" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section className="desk-breakdown desk-breakdown--calc" role="dialog" aria-modal="true" aria-label="Exposure calculation log">
        <header><div><span className="f0-kicker">CALCULATION LOG</span><h2>How was this calculated?</h2></div><Button variant="ghost" size="small" onClick={onClose}>Close</Button></header>
        <CalcLog entries={entries} />
      </section>
    </div>
  )
}
