import { useMemo, useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { useParams, useSearchParams } from 'react-router-dom'
import { apiRequest } from '../../api/client'
import { FACTORY_ID, useExposureMap, useStressTest } from '../../api/hooks/useDeskData'
import { useSpof } from '../../api/hooks/useSpof'
import { CalcLog, Money } from '../../components/domain'
import { Button, Frame, Nameplate, Skeleton, Slider, Toast } from '../../components/primitives'
import { useRelayNavigate } from '../../app/navigation'
import { ShiftChart } from './ShiftChart'
import { ZonePickerMap } from './ZonePickerMap'
import geometry from '../../data/exposureGeometry.json'
import scopes from '../../data/scenarioScopes.json'
import { useUiStore } from '../../store/ui'

const hazards = [
  { value: 'FLOOD', glyph: '≋', label: 'Flood' },
  { value: 'POWER_OUTAGE', glyph: 'ϟ', label: 'Power' },
  { value: 'WATER_OUTAGE', glyph: '≈', label: 'Water' },
  { value: 'ACCESS_BLOCKED', glyph: '⊣', label: 'Access' },
  { value: 'RESOURCE_DOWN', glyph: '▣', label: 'Resource' },
]

const scopeTypes = [
  { value: 'zone', label: 'Zone' },
  { value: 'cluster', label: 'Cluster' },
  { value: 'grid', label: 'Grid' },
  { value: 'sites', label: 'Sites' },
  { value: 'exposure_alert', label: 'Current alert' },
  { value: 'resource', label: 'Resource' },
]

export default function WhatIf() {
  const navigate = useRelayNavigate()
  const snapshotMode = useUiStore((state) => state.snapshotMode)
  const { id } = useParams()
  const [searchParams] = useSearchParams()
  const autoTest = useStressTest(id)
  const spof = useSpof()
  const siteMap = useExposureMap()
  const initialHazard = hazards.some((item) => item.value === searchParams.get('hazard'))
    ? searchParams.get('hazard')
    : 'FLOOD'
  const [hazard, setHazard] = useState(initialHazard)
  const [scopeType, setScopeType] = useState(initialHazard === 'RESOURCE_DOWN' ? 'resource' : initialHazard === 'POWER_OUTAGE' ? 'grid' : 'zone')
  const [scopeIds, setScopeIds] = useState(() => {
    const resourceId = searchParams.get('resource_id')
    return resourceId ? [resourceId] : initialHazard === 'RESOURCE_DOWN' ? [] : ['zone_ambattur_north']
  })
  const [startHours, setStartHours] = useState(24)
  const [durationHours, setDurationHours] = useState(72)
  const [traceOpen, setTraceOpen] = useState(false)
  const [recoveryError, setRecoveryError] = useState(null)

  const manualTest = useMutation({
    mutationFn: (scenario) => apiRequest('/stress-tests', {
      method: 'POST',
      body: JSON.stringify({
        factory_id: FACTORY_ID,
        hazard: scenario.hazard,
        scope: { type: scenario.scopeType, ids: scenario.scopeIds },
        start_in_hours: scenario.startHours,
        duration_hours: scenario.durationHours,
      }),
    }),
  })

  const result = id ? autoTest.data : manualTest.data
  const optionList = useMemo(() => {
    if (scopeType === 'zone') return geometry.zones.map((zone) => ({ id: zone.id, label: zone.name }))
    if (scopeType === 'cluster') return scopes.clusters.map((cluster) => ({ id: cluster, label: cluster.replaceAll('_', ' ') }))
    if (scopeType === 'grid') return scopes.grids.map((grid) => ({ id: grid, label: grid.replaceAll('_', ' ') }))
    if (scopeType === 'sites') return (siteMap.data?.points || []).map((point) => ({ id: point.site_id, label: point.name }))
    if (scopeType === 'resource') {
      return (spof.data?.nodes || [])
        .filter((node) => ['machine', 'vendor', 'supplier'].includes(node.kind))
        .map((node) => ({ id: node.id, label: `${node.name} · ${node.kind}` }))
    }
    return []
  }, [scopeType, siteMap.data, spof.data])

  const hasAlertSites = (siteMap.data?.points || []).filter((point) => point.site_risk >= 50).map((point) => point.site_id)

  const updateHazard = (value) => {
    setHazard(value)
    if (value === 'RESOURCE_DOWN') {
      setScopeType('resource')
      setScopeIds(searchParams.get('resource_id') ? [searchParams.get('resource_id')] : [])
    } else if (value === 'POWER_OUTAGE') {
      setScopeType('grid')
      setScopeIds(['grid_chennai_metro'])
    } else {
      setScopeType('zone')
      setScopeIds(['zone_ambattur_north'])
    }
  }

  const updateScopeType = (value) => {
    setScopeType(value)
    if (value === 'zone') setScopeIds(['zone_ambattur_north'])
    else if (value === 'cluster') setScopeIds(['cl_ambattur'])
    else if (value === 'grid') setScopeIds(['grid_chennai_metro'])
    else if (value === 'sites') setScopeIds(['fac_owner'])
    else if (value === 'resource') setScopeIds(searchParams.get('resource_id') ? [searchParams.get('resource_id')] : [])
    else setScopeIds(hasAlertSites)
  }

  const toggleScopeId = (value) => {
    setScopeIds((current) => current.includes(value) ? current.filter((item) => item !== value) : [...current, value])
  }

  const run = () => {
    const ids = scopeType === 'exposure_alert' ? hasAlertSites : scopeIds
    manualTest.mutate({ hazard, scopeType, scopeIds: ids, startHours, durationHours })
  }

  const openRecovery = async (orderId, stressId) => {
    setRecoveryError(null)
    try {
      const request = await apiRequest('/recovery-requests', {
        method: 'POST',
        body: JSON.stringify({ from_stress_test_id: stressId, order_id: orderId }),
      })
      useUiStore.getState().setPreference('presenterRecoveryId', request.id)
      navigate(`/app/recovery/${request.id}`)
    } catch (requestError) {
      setRecoveryError(requestError.message)
    }
  }

  const loading = id ? autoTest.isLoading : false
  const error = id ? autoTest.error : manualTest.error
  const exposeError = siteMap.error || spof.error

  if (id && loading) {
    return <main className="whatif-page"><div className="f0-kicker">SCENARIO · AUTO-RUN</div><h1>WHAT-IF</h1><Skeleton lines={6} /></main>
  }

  return (
    <main className="whatif-page">
      <header className="whatif-heading">
        <div><span className="f0-kicker">DISRUPTION SIMULATION · SAMPLE DATA</span><h1>WHAT-IF</h1></div>
        {id && <Nameplate>AUTO-RUN · READ ONLY</Nameplate>}
      </header>

      {exposeError && <Toast tone="warning">Scope data could not be fully loaded. Retry the related screen to restore choices.</Toast>}
      {error && (
        <Toast tone="warning">STRESS TEST FAILED · {error.code || 'REQUEST_ERROR'} · {error.message}</Toast>
      )}
      {recoveryError && <Toast tone="warning">RECOVERY REQUEST FAILED · {recoveryError}</Toast>}

      {!id && (
        <section className="whatif-workspace">
          <Frame className="whatif-scenario">
            <span className="f0-kicker">SCENARIO</span>
            <h2>Choose a disruption</h2>
            <div className="whatif-hazards" role="group" aria-label="Hazard type">
              {hazards.map((item) => (
                <button key={item.value} type="button" className={hazard === item.value ? 'is-selected' : ''} aria-pressed={hazard === item.value} onClick={() => updateHazard(item.value)}>
                  <span aria-hidden="true">{item.glyph}</span><small>{item.label}</small>
                </button>
              ))}
            </div>
            <label className="whatif-label" htmlFor="scope-type">Scope</label>
            <select id="scope-type" value={scopeType} onChange={(event) => updateScopeType(event.target.value)}>
              {scopeTypes.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}
            </select>

            {scopeType === 'exposure_alert' ? (
              <div className="whatif-current-alert">
                <span className="f0-kicker">CURRENT ALERT SITES</span>
                {hasAlertSites.length
                  ? hasAlertSites.map((siteId) => <Nameplate key={siteId}>{siteId}</Nameplate>)
                  : <p>No active exposure alert sites.</p>}
              </div>
            ) : (
              <div className="whatif-options">
                {optionList.map((option) => (
                  <label key={option.id}>
                    <input type="checkbox" checked={scopeIds.includes(option.id)} onChange={() => toggleScopeId(option.id)} />
                    <span>{option.label}</span>
                  </label>
                ))}
                {!optionList.length && <p>No scope choices available.</p>}
              </div>
            )}

            {scopeType === 'zone' && (
              <ZonePickerMap selectedId={scopeIds[0]} onSelect={(zoneId) => setScopeIds([zoneId])} />
            )}

            <Slider label="Starts in (hours)" min={0} max={72} step={1} value={startHours} onChange={setStartHours} />
            <Slider label="Duration (hours)" min={6} max={120} step={6} value={durationHours} onChange={setDurationHours} />
            <Button disabled={snapshotMode || manualTest.isPending || (scopeType !== 'exposure_alert' && scopeIds.length === 0)} loading={manualTest.isPending} onClick={run}>Run test</Button>
          </Frame>

          <section className="whatif-results">
            {!result ? (
              <Frame className="whatif-empty">
                <span className="f0-kicker">SHIFT CHART</span>
                <h2>Scenario results appear here</h2>
                <p>Choose a hazard, scope, start and duration, then run the test. The schedule compares baseline completion against the stressed schedule.</p>
              </Frame>
            ) : <StressResults result={result} onOpenRecovery={openRecovery} onShowTrace={() => setTraceOpen(true)} readOnly={snapshotMode} />}
          </section>
        </section>
      )}

      {id && (result ? (
        <StressResults result={result} onOpenRecovery={openRecovery} onShowTrace={() => setTraceOpen(true)} readOnly={snapshotMode} />
      ) : autoTest.isError ? (
        <Frame className="whatif-empty"><Nameplate>{autoTest.error.code || 'NOT_FOUND'}</Nameplate><p>{autoTest.error.message}</p><Button variant="secondary" onClick={() => autoTest.refetch()}>Retry</Button></Frame>
      ) : null)}

      {traceOpen && result && <TraceDrawer trace={result.trace || []} onClose={() => setTraceOpen(false)} />}
    </main>
  )
}

function StressResults({ result, onOpenRecovery, onShowTrace, readOnly = false }) {
  const summary = result.summary
  return (
    <div className="whatif-result-stack">
      <Frame className="whatif-summary">
        <div className="whatif-summary__headline">
          <div><span className="f0-kicker">{result.trigger === 'AUTO' ? 'AUTO TEST · READ ONLY' : 'STRESS TEST RESULT'}</span><h2>{result.headline}</h2></div>
          <Nameplate>{result.hazard}</Nameplate>
        </div>
        <div className="whatif-summary__metrics">
          <Metric label="Orders at risk" value={summary.orders_at_risk} />
          <Metric label="Revenue exposed" value={<Money value={summary.revenue_exposed_inr} />} />
          <Metric label="No fallback" value={summary.orders_no_fallback} />
          <Metric label="No ready fallback" value={summary.orders_no_ready_fallback} />
        </div>
      </Frame>
      <Frame className="whatif-shift">
        <header className="whatif-shift__heading">
          <div><span className="f0-kicker">T+00 ───────────────────────── T+168 h</span><h2>Shift chart</h2></div>
          <Button variant="ghost" size="small" onClick={onShowTrace}>Calc log</Button>
        </header>
          <ShiftChart result={result} onOpenRecovery={(orderId) => onOpenRecovery(orderId, result.id)} readOnly={readOnly} />
      </Frame>
    </div>
  )
}

function Metric({ label, value }) {
  return <div><span>{label}</span><strong>{value}</strong></div>
}

function TraceDrawer({ trace, onClose }) {
  return (
    <div className="whatif-overlay" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section className="whatif-trace" role="dialog" aria-modal="true" aria-label="Stress test calculation log">
        <header><div><span className="f0-kicker">CALCULATION LOG</span><h2>How was this calculated?</h2></div><Button variant="ghost" size="small" onClick={onClose}>Close</Button></header>
        <CalcLog entries={trace} />
      </section>
    </div>
  )
}
