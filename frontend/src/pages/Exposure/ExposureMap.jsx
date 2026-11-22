import { useEffect, useMemo, useState } from 'react'
import { Circle, CircleMarker, MapContainer, Polyline, TileLayer, Tooltip, useMap } from 'react-leaflet'
import geometry from '../../data/exposureGeometry.json'
import { Frame } from '../../components/primitives'

const palette = {
  LOW: 'low',
  MODERATE: 'moderate',
  HIGH: 'high',
  SEVERE: 'severe',
}

export function ExposureMap({ points, routeRisks = [], selectedSiteId, onSelect, mode }) {
  const [tilesFailed, setTilesFailed] = useState(false)
  const routeRiskById = useMemo(() => new Map(routeRisks.map((route) => [route.route_id, route])), [routeRisks])
  const bounds = useMemo(() => {
    // Start on the active Chennai storm footprint so the curated zones and
    // short exit routes remain legible. The ranked list still contains every site.
    const local = points.filter((point) => point.lat >= 12.8 && point.lat <= 13.2 && point.lon >= 79.8 && point.lon <= 80.3)
    const coords = local.map((point) => [point.lat, point.lon])
    for (const route of geometry.routes) {
      for (const sample of route.samples) coords.push([sample.lat, sample.lon])
    }
    for (const zone of geometry.zones) coords.push([zone.center_lat, zone.center_lon])
    return coords.length ? coords : [[13.1, 80.15], [13.1, 80.15]]
  }, [points])
  const selected = points.find((point) => point.site_id === selectedSiteId)

  return (
    <Frame className="exposure-map-frame">
      <MapContainer
        className={`exposure-map ${tilesFailed ? 'tiles-failed' : ''}`}
        bounds={bounds}
        boundsOptions={{ padding: [32, 32] }}
        scrollWheelZoom
        zoomControl
      >
        <FocusSelectedSite selected={selected} />
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution="&copy; OpenStreetMap contributors"
          eventHandlers={{ tileerror: () => setTilesFailed(true), tileload: () => setTilesFailed(false) }}
        />
        {geometry.zones.map((zone) => (
          <Circle
            key={zone.id}
            center={[zone.center_lat, zone.center_lon]}
            radius={zone.radius_m}
            pathOptions={{
              className: 'exposure-zone',
            }}
          >
            <Tooltip>{zone.name} · illustrative planning zone, not an official flood map</Tooltip>
          </Circle>
        ))}
        {geometry.routes.map((route) => {
          const risk = routeRiskById.get(route.route_id)?.route_risk
          const exposed = risk != null && risk >= 50
          return (
            <Polyline
              key={route.route_id}
              positions={route.samples.map((sample) => [sample.lat, sample.lon])}
              pathOptions={{
                className: `exposure-route ${exposed ? 'exposure-route--exposed' : ''} ${risk == null ? 'exposure-route--unknown' : ''}`,
              }}
            >
              <Tooltip>{route.exit_name} · route risk {risk ?? 'unavailable'}</Tooltip>
            </Polyline>
          )
        })}
        {points.map((point) => (
          <CircleMarker
            key={point.site_id}
            center={[point.lat, point.lon]}
            radius={point.role === 'OWNER' ? 9 : 6}
            pathOptions={{
              className: `exposure-site-marker exposure-site-marker--${palette[point.risk_level] || 'low'} ${selectedSiteId === point.site_id ? 'is-selected' : ''}`,
            }}
            eventHandlers={{ click: () => onSelect(point.site_id) }}
          >
            <Tooltip direction="top">{point.name} · {point.site_risk}/100 · {point.risk_level}</Tooltip>
          </CircleMarker>
        ))}
      </MapContainer>
      {tilesFailed && <div className="exposure-map__offline" role="status">MAP TILES UNAVAILABLE · VECTOR OVERLAYS ACTIVE</div>}
      <div className="exposure-map__badge">
        {mode?.toUpperCase() || 'WEATHER'} · RISK INDICATOR, NOT A FLOOD MODEL
      </div>
    </Frame>
  )
}

function FocusSelectedSite({ selected }) {
  const map = useMap()
  const selectedId = selected?.site_id
  const lat = selected?.lat
  const lon = selected?.lon
  useEffect(() => {
    if (!selectedId || lat == null || lon == null) return
    const location = [lat, lon]
    if (!map.getBounds().contains(location)) map.flyTo(location, 9, { duration: 0.45 })
  }, [map, selectedId, lat, lon])
  return null
}
