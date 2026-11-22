import { Circle, MapContainer, TileLayer, Tooltip } from 'react-leaflet'
import geometry from '../../data/exposureGeometry.json'

export function ZonePickerMap({ selectedId, onSelect }) {
  return (
    <div className="whatif-zone-map">
      <MapContainer center={[13.06, 80.15]} zoom={9} scrollWheelZoom={false} zoomControl={false}>
        <TileLayer
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          attribution="&copy; OpenStreetMap contributors"
        />
        {geometry.zones.map((zone) => (
          <Circle
            key={zone.id}
            center={[zone.center_lat, zone.center_lon]}
            radius={zone.radius_m}
            pathOptions={{ className: `whatif-zone ${zone.id === selectedId ? 'is-selected' : ''}` }}
            eventHandlers={{ click: () => onSelect(zone.id) }}
          >
            <Tooltip>{zone.name}</Tooltip>
          </Circle>
        ))}
      </MapContainer>
      <span>Curated planning zones · not official flood maps</span>
    </div>
  )
}
