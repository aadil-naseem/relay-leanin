import { useMemo, useState } from 'react'
import { CircleMarker, MapContainer, TileLayer, Tooltip } from 'react-leaflet'
import { Frame } from '../../components/primitives'

const riskColor = {
  LOW: 'var(--c-sky)',
  MODERATE: 'var(--c-pale)',
  HIGH: 'var(--c-sun)',
  SEVERE: 'var(--c-sun)',
}

export function ExposureMiniMap({ points = [], routes = [] }) {
  const [tilesFailed, setTilesFailed] = useState(false)
  const bounds = useMemo(() => {
    const locations = points.filter((point) => Number.isFinite(point.lat) && Number.isFinite(point.lon))
    return locations.length ? locations.map((point) => [point.lat, point.lon]) : [[13.1, 80.15]]
  }, [points])

  return (
    <Frame className="desk-map">
      <div className="desk-panel__heading">
        <div><span className="f0-kicker">SITE EXPOSURE</span><h2>Regional picture</h2></div>
        <a href="/app/exposure">OPEN MAP →</a>
      </div>
      <div className={`desk-map__canvas ${tilesFailed ? 'tiles-failed' : ''}`}>
        <MapContainer
          className="desk-leaflet"
          bounds={bounds}
          boundsOptions={{ padding: [16, 16] }}
          scrollWheelZoom={false}
          zoomControl={false}
          attributionControl
        >
          <TileLayer
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution="&copy; OpenStreetMap contributors"
            eventHandlers={{ tileerror: () => setTilesFailed(true), tileload: () => setTilesFailed(false) }}
          />
          {points.map((point) => (
            <CircleMarker
              key={point.site_id}
              center={[point.lat, point.lon]}
              radius={point.role === 'OWNER' ? 8 : 5}
              pathOptions={{
                color: riskColor[point.risk_level] || 'var(--c-sky)',
                fillColor: riskColor[point.risk_level] || 'var(--c-sky)',
                fillOpacity: point.role === 'OWNER' ? 0.95 : 0.75,
                weight: point.risk_level === 'SEVERE' ? 3 : 1.5,
              }}
            >
              <Tooltip direction="top">{point.name} · {point.site_risk}/100 · {point.risk_level}</Tooltip>
            </CircleMarker>
          ))}
        </MapContainer>
        {tilesFailed && <div className="desk-map__offline" role="status">Map tiles unavailable · site markers remain available</div>}
      </div>
      <div className="desk-map__legend">
        <span><i className="risk-dot risk-dot--sky" />LOW</span>
        <span><i className="risk-dot risk-dot--pale" />MODERATE</span>
        <span><i className="risk-dot risk-dot--sun" />HIGH / SEVERE</span>
      </div>
      {routes.length > 0 && (
        <div className="desk-map__routes" aria-label="Owner access route risks">
          {routes.map((route) => (
            <span key={route.exit_id}>{route.exit_id.replace('exit_', '')} · {route.route_risk ?? '—'}</span>
          ))}
        </div>
      )}
      <p className="desk-map__note">Markers show site risk. Route geometry is not included in the current map API.</p>
    </Frame>
  )
}
