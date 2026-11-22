const risk = {
  LOW: { label: 'Low', tone: 'sky', glyph: '●', shape: 'ring' },
  MODERATE: { label: 'Moderate', tone: 'pale', glyph: '●', shape: 'dot' },
  HIGH: { label: 'High', tone: 'sun', glyph: '▲', shape: 'triangle' },
  SEVERE: { label: 'Severe', tone: 'sun', glyph: '▲!', shape: 'chevron' },
}

const order = {
  ON_TRACK: { label: 'On track', tone: 'sky', glyph: '✓', shape: 'tick' },
  AT_RISK: { label: 'At risk', tone: 'pale', glyph: '◷', shape: 'clock' },
  LATE: { label: 'Late', tone: 'sun', glyph: '⚑', shape: 'flag' },
}

const fallback = {
  READY: { label: 'Ready cover', tone: 'sky', glyph: '⬡', shape: 'shield-solid' },
  POTENTIAL_ONLY: { label: 'Candidate only', tone: 'pale', glyph: '⬡', shape: 'shield-outline' },
  NONE: { label: 'No cover', tone: 'gold', glyph: '⊗', shape: 'shield-cross' },
}

const backup = {
  READY: { label: 'Ready', tone: 'sky', glyph: '⏚', shape: 'closed-contact' },
  STALE: { label: 'Reconfirm needed', tone: 'sky', glyph: '◷', shape: 'dashed-clock' },
  APPROVAL_PENDING: { label: 'Approval pending', tone: 'pale', glyph: '◐', shape: 'half-circle' },
  ASSESSMENT_IN_PROGRESS: { label: 'Assessing', tone: 'navy-light', glyph: '•••', shape: 'three-dots' },
  POTENTIAL_MATCH: { label: 'Potential', tone: 'hair', glyph: '○', shape: 'ring' },
  UNAVAILABLE_EXPIRED: { label: 'Unavailable', tone: 'navy', glyph: '⏚', shape: 'struck-open-contact' },
}

const confidence = {
  HIGH: { label: 'High confidence', tone: 'sky', bars: 3 },
  MEDIUM: { label: 'Medium confidence', tone: 'pale', bars: 2 },
  LOW: { label: 'Low confidence', tone: 'sun', bars: 1 },
  MISSING: { label: 'Missing', tone: 'hair', bars: 0 },
  CONFIRMED: { label: 'Confirmed by person', tone: 'cream', bars: 3 },
}

const weather = {
  live: { label: 'Live', tone: 'sky', glyph: '●' },
  cache: { label: 'Last good', tone: 'pale', glyph: '●' },
  replay: { label: 'Replay', tone: 'pale', glyph: '↻' },
  synthetic: { label: 'Synthetic', tone: 'gold', glyph: '▧' },
}

// Plain-language reasons. The API returns short codes; the UI should explain
// them the way an operator would say them out loud.
const exclusionReason = {
  SAME_CLUSTER: 'in the same industrial cluster as you',
  SAME_HAZARD_ZONE: 'in the same flood zone as you',
  SAME_GRID: 'on the same power grid as you',
  ALSO_EXPOSED_SAME_EVENT: 'in the same storm footprint as you',
  NEARBY: 'too close to your site',
}

const readinessReason = {
  NO_PARTNER_ELIGIBLE: 'no capable partner',
  NOT_READY: 'partner not ready yet',
  STALE: 'partner confirmation expired',
  CORRELATED: 'every capable partner shares your risk',
  TOO_SLOW: 'partner too slow for the deadline',
  NO_CAPACITY: 'partner has no spare capacity',
  UNASSIGNED: 'no backup assigned',
}

const routeStep = {
  REQUEST_SENT: 'Request sent',
  PARTNER_RESPONSE: 'Partner response',
  TECHNICAL_AND_CUSTOMER_APPROVALS: 'Technical and customer approvals',
  PRODUCTION_SCHEDULED: 'Production scheduled',
  PRODUCTION_STARTED: 'Production started',
  QUALITY_INSPECTION: 'Quality inspection',
  DISPATCH_AND_DELIVERY: 'Dispatch and delivery',
}

const processName = {
  TURN: 'Turning',
  MILL: 'Milling',
  DRILL_TAP: 'Drill and tap',
  GRIND_CYL: 'Cylindrical grinding',
  GRIND_SURF: 'Surface grinding',
  WIRE_EDM: 'Wire EDM',
  HEAT_TREAT: 'Heat treatment',
  SURFACE_TREAT: 'Surface treatment',
}

const recoveryStatus = {
  OPEN: 'Open',
  ACTIVE: 'Partner engaged',
  IN_PROGRESS: 'In progress',
  COMPLETE: 'Complete',
  CANCELLED: 'Cancelled',
}

const hazardLabel = {
  FLOOD: 'Flood',
  POWER_OUTAGE: 'Power outage',
  WATER_OUTAGE: 'Water outage',
  ACCESS_BLOCKED: 'Access blocked',
  RESOURCE_DOWN: 'Resource down',
}

/** Turn an unknown CODE_LIKE_value into "Code like value" as a last resort. */
export function humanizeEnum(value) {
  if (!value) return ''
  const words = String(value).toLowerCase().replaceAll('_', ' ').trim()
  return words.charAt(0).toUpperCase() + words.slice(1)
}

export const backupStatusLabel = (value) => backup[value]?.label || humanizeEnum(value)
export const orderStateLabel = (value) => order[value]?.label || humanizeEnum(value)

/** "ord_104" reads as an internal id; show "Order 104" to a person. */
export const orderLabel = (id) => {
  if (!id) return 'Order'
  const digits = String(id).replace(/^ord_?/i, '').replace(/^0+(?=\d)/, '')
  return digits ? `Order ${digits}` : String(id)
}
export const exclusionReasonLabel = (reason) => (reason ? (exclusionReason[reason] || humanizeEnum(reason)) : 'correlated risk')
export const readinessReasonLabel = (reason) => (reason ? (readinessReason[reason] || humanizeEnum(reason)) : 'no backup assigned')
export const routeStepLabel = (key) => routeStep[key] || humanizeEnum(key)
export const recoveryStatusLabel = (value) => recoveryStatus[value] || humanizeEnum(value)
export const hazardName = (value) => hazardLabel[value] || humanizeEnum(value)
export const processLabel = (code) => processName[code] || humanizeEnum(code)

/** Step names arrive as "GRIND_CYL (seq 3)"; name the process for the reader. */
export const stepLabel = (name) => String(name ?? '').replace(/^([A-Z][A-Z_]+)/, (code) => processLabel(code))

export const statusStyle = (kind, value, reason) => {
  const source = { risk, order, fallback, backup, confidence, weather }[kind]
  const item = source?.[value]
  if (!item) return { label: value || 'Unknown', tone: 'hair', glyph: '·', shape: 'unknown' }
  return kind === 'backup' && reason
    ? { ...item, label: `Excluded · ${exclusionReasonLabel(reason)}`, tone: 'gold', glyph: '⏚', shape: 'hatch-navy' }
    : item
}
