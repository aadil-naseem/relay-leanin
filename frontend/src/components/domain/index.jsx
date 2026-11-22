import { useEffect, useState } from 'react'
import { formatMoney, formatOdometerValue } from '../../lib/format'
import { exclusionReasonLabel, routeStepLabel, statusStyle } from '../../lib/status'
import { Button, Chip, Frame, Nameplate, Stamp } from '../primitives'

export function StatusPill({ kind, value, reason }) {
  const item = statusStyle(kind, value, reason)
  return (
    <span className={`relay-status relay-status--${item.tone} relay-status--${item.shape}`}>
      <span className="relay-status__glyph" aria-hidden="true">{item.glyph}</span>
      <span>{item.label}</span>
    </span>
  )
}

export function RiskPill({ value }) {
  return <StatusPill kind="risk" value={value} />
}

export function OrderStatePill({ value }) {
  return <StatusPill kind="order" value={value} />
}

export function FallbackShield({ value }) {
  return <StatusPill kind="fallback" value={value} />
}

export function BackupStatusPill({ value, excludedReason }) {
  if (excludedReason) return <StatusPill kind="backup" value={value} reason={excludedReason} />
  return <StatusPill kind="backup" value={value} />
}

export function ConfidenceBars({ value }) {
  const item = statusStyle('confidence', value)
  return (
    <span className={`relay-confidence relay-confidence--${item.tone}`} aria-label={item.label} title={item.label}>
      <span className="relay-confidence__bars" aria-hidden="true">
        {[1, 2, 3].map((bar) => <i key={bar} className={bar <= item.bars ? 'is-on' : ''} />)}
      </span>
      <span>{item.label}</span>
    </span>
  )
}

export function ExcludedReason({ reason }) {
  return <span className="relay-excluded"><i aria-hidden="true" /> Excluded · {exclusionReasonLabel(reason)}</span>
}

export function DataLabelBadge({ children = 'SAMPLE / SIMULATED' }) {
  return <Stamp tone="gold">{children}</Stamp>
}

export function WeatherSourceBadge({ source = 'replay', degraded = false }) {
  const item = statusStyle('weather', source)
  return (
    <span className={`relay-weather relay-weather--${item.tone}`}>
      <i aria-hidden="true">{item.glyph}</i>
      <span>{item.label}</span>
      {degraded && <b aria-label="Degraded data">!</b>}
    </span>
  )
}

export function Money({ value, className = '' }) {
  return <span className={`relay-money ${className}`.trim()}>{formatMoney(value)}</span>
}

export function Odometer({ value, decimals = 0, suffix = '', label }) {
  const [display, setDisplay] = useState(() => formatOdometerValue(value, decimals))
  useEffect(() => {
    const frame = window.requestAnimationFrame(() => setDisplay(formatOdometerValue(value, decimals)))
    return () => window.cancelAnimationFrame(frame)
  }, [value, decimals])
  return <span className="relay-odometer" aria-label={label || `${display}${suffix}`}><span>{display}</span>{suffix && <small>{suffix}</small>}</span>
}

export function StackLight({ exposure = 'LOW', readiness = 0, freshness = 'replay' }) {
  const readinessTone = readiness >= 60 ? 'sky' : readiness >= 30 ? 'pale' : 'sun'
  const exposureTone = exposure === 'SEVERE' || exposure === 'HIGH'
    ? 'sun'
    : exposure === 'MODERATE' ? 'pale' : 'sky'
  const lamps = [
    { label: `Exposure ${exposure}`, tone: exposureTone },
    { label: `Readiness ${readiness}`, tone: readinessTone },
    { label: `Data ${freshness}`, tone: freshness === 'live' ? 'sky' : 'pale' },
  ]
  return (
    <span className="relay-stack-light" aria-label={lamps.map((lamp) => lamp.label).join(', ')} title={lamps.map((lamp) => lamp.label).join(' · ')}>
      {lamps.map((lamp, index) => <i key={index} className={`relay-lamp relay-lamp--${lamp.tone}`} />)}
    </span>
  )
}

export function ShiftClock({ time = '--:--' }) {
  return <time className="relay-shift-clock">{time} IST</time>
}

export function HorizonBar({ onsetHours, horizonHours = 72 }) {
  const position = Math.min(100, Math.max(0, ((onsetHours ?? 0) / horizonHours) * 100))
  return (
    <div className="relay-horizon" aria-label={`Forecast horizon, onset ${onsetHours ?? 'unknown'} hours`}>
      <span>T+00</span><i><b style={{ left: `${position}%` }} /></i><span>T+{horizonHours}</span>
    </div>
  )
}

export function ReadinessRing({ score = 0, weighted, size = 148 }) {
  const radius = 57
  const circumference = 2 * Math.PI * radius
  const covered = Math.min(100, Math.max(0, Number(score) || 0))
  return (
    <div className="relay-readiness" style={{ width: size }}>
      <div className="relay-readiness__face" style={{ width: size, height: size }}>
        <svg viewBox="0 0 140 140" role="img" aria-label={`Readiness ${covered} out of 100`}>
          <circle className="relay-readiness__track" cx="70" cy="70" r={radius} />
          <circle className="relay-readiness__gap" cx="70" cy="70" r={radius} />
          <circle className="relay-readiness__fill" cx="70" cy="70" r={radius}
            style={{ strokeDasharray: circumference, strokeDashoffset: circumference * (1 - covered / 100) }} />
        </svg>
        <span className="relay-readiness__value">{formatOdometerValue(covered)}<small>/100</small></span>
      </div>
      {weighted !== undefined && <span className="relay-readiness__weighted">weighted score {formatOdometerValue(weighted)}</span>}
    </div>
  )
}

export function AlertBanner({ level = 'HIGH', headline, onset, action, onAction, disabled = false }) {
  return (
    <Frame className={`relay-alert relay-alert--${String(level).toLowerCase()}`}>
      <div className="relay-alert__copy">
        <StatusPill kind="risk" value={level} />
        <strong>{headline || 'Risk indicator: review the affected sites and orders.'}</strong>
        {onset !== undefined && <span className="relay-mono">ONSET T+{onset}h</span>}
      </div>
      {action && <Button disabled={disabled} onClick={onAction}>{action}</Button>}
    </Frame>
  )
}

export function DimensionLine({ value, label }) {
  return <span className="relay-dimension"><i aria-hidden="true" /><b>{value}</b>{label && <small>{label}</small>}<i aria-hidden="true" /></span>
}

export function CalcLog({ entries = [], title = 'How was this calculated?' }) {
  return (
    <details className="relay-calc-log">
      <summary>{title}</summary>
      {!entries.length ? <p>No calculation trace available.</p> : (
        <ol>{entries.map((entry, index) => (
          <li key={`${entry.step}-${index}`}>
            <Nameplate>{entry.step}</Nameplate>
            <p>{entry.detail}</p>
            {(entry.inputs || entry.output) && <pre>{JSON.stringify({ inputs: entry.inputs, output: entry.output }, null, 2)}</pre>}
          </li>
        ))}</ol>
      )}
    </details>
  )
}

export function PaperSheet({ title, watermark, children, className = '' }) {
  return (
    <article className={`relay-paper ${className}`.trim()}>
      {watermark && <span className="relay-paper__watermark" aria-hidden="true">{watermark}</span>}
      {title && <header>{title}</header>}
      <div className="relay-paper__body">{children}</div>
    </article>
  )
}

export function RelayCircuit({ partners = [] }) {
  return (
    <div className="relay-circuit" aria-label="Owner to backup partner circuit">
      <Nameplate>OWNER</Nameplate>
      <span className="relay-circuit__bus" aria-hidden="true" />
      {partners.map((partner) => (
        <div className={`relay-circuit__partner relay-circuit__partner--${String(partner.effective_status || partner.status).toLowerCase()}`} key={partner.partner_id}>
          <i aria-hidden="true">◯</i><span>{partner.name}</span><StatusPill kind="backup" value={partner.effective_status || partner.status} />
        </div>
      ))}
    </div>
  )
}

export function ShiftChart({ rows = [] }) {
  return (
    <div className="relay-shift-chart" role="table" aria-label="Shift schedule">
      {rows.map((row) => (
        <div className="relay-shift-chart__row" role="row" key={row.id}>
          <Nameplate>{row.id}</Nameplate>
          <div className="relay-shift-chart__track">
            <i className="relay-shift-chart__base" style={{ width: `${row.baseline ?? 0}%` }} />
            <i className="relay-shift-chart__stressed" style={{ width: `${row.stressed ?? 0}%` }} />
          </div>
          <OrderStatePill value={row.state || 'ON_TRACK'} />
        </div>
      ))}
    </div>
  )
}

export function DependencyGraph({ nodes = [], edges = [] }) {
  return (
    <div className="relay-dependency-graph">
      <div className="relay-dependency-graph__nodes">
        {nodes.map((node) => <Nameplate key={node.id}>{node.name || node.id}</Nameplate>)}
      </div>
      <p className="relay-mono">{edges.length} dependency links</p>
    </div>
  )
}

export function CandidateCard({ candidate, onSelect }) {
  const excluded = Boolean(candidate?.excluded)
  return (
    <Frame className={`relay-candidate ${excluded ? 'is-excluded' : ''}`}>
      <h3>{candidate?.name || 'Candidate'}</h3>
      <BackupStatusPill value={candidate?.effective_status || candidate?.status} excludedReason={candidate?.exclusion_reason && excluded ? candidate.exclusion_reason : null} />
      {candidate?.filters && <ul>{candidate.filters.map((filter) => <li key={filter.key}>{filter.result} · {filter.key}</li>)}</ul>}
      <Button disabled={excluded || !onSelect} variant={excluded ? 'ghost' : 'secondary'} onClick={() => onSelect?.(candidate)}>
        {excluded ? 'Cannot select' : 'Select partner'}
      </Button>
    </Frame>
  )
}

export function RouteCard({ steps = [], onAdvance }) {
  return (
    <section className="relay-route-card">
      <ol>{steps.map((step) => <li className={step.state === 'DONE' ? 'is-done' : ''} key={step.step_key}>{routeStepLabel(step.step_key)}</li>)}</ol>
      <Button variant="secondary" disabled={!onAdvance} onClick={onAdvance}>Advance simulated step →</Button>
      <small>SIMULATED TRACKING</small>
    </section>
  )
}

export function RedactionSheet({ original, redacted, report }) {
  return (
    <div className="relay-redaction-sheet">
      <PaperSheet title="Original (owner view)">{original}</PaperSheet>
      <PaperSheet title="Redacted RFQ">
        {redacted}
        {!!report?.scrubbed_text_fields?.length && <div className="relay-redaction-bars" aria-label="Text redacted"><i /><i /><i /></div>}
      </PaperSheet>
    </div>
  )
}

export function StackLightStatus({ data }) {
  return <Chip tone={data?.source === 'live' ? 'sky' : 'pale'}>{data?.source || 'unknown'}{data?.degraded ? ' · DEGRADED' : ''}</Chip>
}
