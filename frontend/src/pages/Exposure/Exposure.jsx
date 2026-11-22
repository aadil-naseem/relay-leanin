import { useMemo, useState } from 'react'
import { useExposureMap, useOwnerExposure } from '../../api/hooks/useDeskData'
import { CalcLog, DimensionLine, RiskPill, WeatherSourceBadge } from '../../components/domain'
import { Button, Frame, Nameplate, Skeleton, Toast } from '../../components/primitives'
import { ExposureMap } from './ExposureMap'

export default function Exposure() {
  const map = useExposureMap()
  const owner = useOwnerExposure()
  const [selectedSiteId, setSelectedSiteId] = useState('fac_owner')
  const [calcOpen, setCalcOpen] = useState(false)

  const points = useMemo(
    () => [...(map.data?.points || [])].sort((a, b) => b.site_risk - a.site_risk),
    [map.data?.points],
  )
  const selected = points.find((point) => point.site_id === selectedSiteId) || points[0]
  const isOwner = selected?.site_id === 'fac_owner'
  const drivers = isOwner ? owner.data?.site?.drivers || [] : []
  const ownerSite = owner.data?.site
  const routeRisks = owner.data?.routes || []

  if (map.isLoading || owner.isLoading) {
    return (
      <main className="exposure-page">
        <div className="f0-kicker">FIELD CONDITIONS</div>
        <h1>EXPOSURE</h1>
        <Skeleton lines={6} />
      </main>
    )
  }

  if (map.isError || owner.isError) {
    const error = map.error || owner.error
    return (
      <main className="exposure-page">
        <div className="f0-kicker">FIELD CONDITIONS</div>
        <h1>EXPOSURE</h1>
        <Frame className="exposure-error">
          <span className="f0-kicker">REQUEST FAILED · {error.code || 'CONNECTION_ERROR'}</span>
          <p>{error.message}</p>
          <Button variant="secondary" onClick={() => { map.refetch(); owner.refetch() }}>Retry</Button>
        </Frame>
      </main>
    )
  }

  const mapData = map.data
  const ownerRisk = ownerSite

  return (
    <main className="exposure-page">
      <header className="exposure-heading">
        <div>
          <span className="f0-kicker">FIELD CONDITIONS · {mapData.mode.toUpperCase()}</span>
          <h1>EXPOSURE</h1>
          <p>Risk indicator from forecast rain and site conditions. Not a flood model.</p>
        </div>
        <div className="exposure-heading__meta">
          <WeatherSourceBadge source={mapData.weather.source} degraded={mapData.weather.degraded} />
          <span className="exposure-attribution">Weather data by Open-Meteo.com</span>
          <span className="exposure-attribution">© OpenStreetMap contributors</span>
        </div>
      </header>

      {mapData.weather.degraded && (
        <Toast tone="warning">
          Showing {mapData.weather.source} data · requested mode {mapData.mode}.
        </Toast>
      )}

      <section className="exposure-workspace">
        <Frame className="exposure-site-panel">
          <header className="exposure-panel-heading">
            <div><span className="f0-kicker">SITES · RANKED BY RISK</span><h2>Storm footprint</h2></div>
          </header>
          <ol className="exposure-site-list">
            {points.map((point, index) => (
              <li key={point.site_id}>
                <button
                  type="button"
                  className={selected?.site_id === point.site_id ? 'is-selected' : ''}
                  aria-pressed={selected?.site_id === point.site_id}
                  onClick={() => setSelectedSiteId(point.site_id)}
                >
                  <span className="exposure-site-list__rank">{String(index + 1).padStart(2, '0')}</span>
                  <span className="exposure-site-list__main">
                    <strong>{point.name}</strong>
                    <small>{point.role} · {point.site_id}</small>
                  </span>
                  <span className="exposure-site-list__score">
                    <b>{point.site_risk}</b><small>/100</small>
                  </span>
                </button>
              </li>
            ))}
            {!points.length && <li className="exposure-empty">No sites returned by the exposure map.</li>}
          </ol>
          <div className="exposure-site-panel__footer">
            <Nameplate>{selected?.site_id || 'NO SITE SELECTED'}</Nameplate>
            {selected && <RiskPill value={selected.risk_level} />}
          </div>
        </Frame>

        <div className="exposure-map-column">
          <ExposureMap
            points={points}
            routeRisks={routeRisks}
            selectedSiteId={selected?.site_id}
            onSelect={setSelectedSiteId}
            mode={mapData.mode}
          />
          <Frame className="exposure-horizon">
            <div className="exposure-panel-heading">
              <div><span className="f0-kicker">NEXT 72 HOURS</span><h2>{selected?.name || 'Selected site'}</h2></div>
              {selected && <RiskPill value={selected.risk_level} />}
            </div>
            {selected && (
              <div className="exposure-horizon__stats">
                <DimensionLine value={`${Math.round(isOwner ? ownerRisk?.max24_mm || 0 : selected.site_risk)}${isOwner ? ' mm' : ''}`} label={isOwner ? 'heaviest 24 h' : 'risk score'} />
                {isOwner && <span className="exposure-onset">ONSET <b>T+{ownerRisk?.onset_in_hours ?? '—'}h</b></span>}
              </div>
            )}
            <p className="exposure-horizon__fallback">
              Hourly forecast samples are not included in the current API response; the time scrubber is unavailable.
            </p>
          </Frame>
        </div>

        <Frame className="exposure-driver-panel">
          <div className="exposure-panel-heading">
            <div><span className="f0-kicker">SITE CONDITIONS</span><h2>What drives risk</h2></div>
          </div>
          {selected ? (
            <>
              <div className="exposure-driver-panel__score"><b>{selected.site_risk}</b><span>/ 100</span><small>{selected.risk_level}</small></div>
              {isOwner && drivers.length ? (
                <ul className="exposure-drivers">{drivers.map((driver, index) => <li key={`${index}-${driver}`}>{driver}</li>)}</ul>
              ) : (
                <p className="exposure-driver-panel__fallback">
                  The map endpoint supplies site risk but not per-site driver detail for this location.
                </p>
              )}
              <div className="exposure-driver-panel__route">
                <span className="f0-kicker">OWNER EXIT ROUTES</span>
                {routeRisks.map((route) => (
                  <div key={route.route_id}>
                    <span>{route.exit_id.replace('exit_', '')}</span>
                    <DimensionLine value={route.route_risk == null ? '—' : `${route.route_risk}`} label="risk" />
                  </div>
                ))}
                {!routeRisks.length && <small>Route facts unavailable · site-only indicator</small>}
              </div>
              <Button variant="ghost" size="small" onClick={() => setCalcOpen(true)}>How was this calculated?</Button>
            </>
          ) : <p>Select a site on the map or list.</p>}
        </Frame>
      </section>

      <CalcDrawer open={calcOpen} onClose={() => setCalcOpen(false)} trace={owner.data?.trace || []} />
      <div className="exposure-bottom-label">ILLUSTRATIVE PLANNING ZONES · NOT OFFICIAL FLOOD MAPS</div>
    </main>
  )
}

function CalcDrawer({ open, onClose, trace }) {
  if (!open) return null
  return (
    <div className="desk-overlay" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section className="desk-breakdown desk-breakdown--calc" role="dialog" aria-modal="true" aria-label="Exposure calculation log">
        <header><div><span className="f0-kicker">CALCULATION LOG</span><h2>How was risk calculated?</h2></div><Button variant="ghost" size="small" onClick={onClose}>Close</Button></header>
        <CalcLog entries={trace} />
      </section>
    </div>
  )
}
