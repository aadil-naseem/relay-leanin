import { useState } from 'react'
import {
  AlertBanner,
  BackupStatusPill,
  CandidateCard,
  ConfidenceBars,
  DataLabelBadge,
  DimensionLine,
  FallbackShield,
  Money,
  Odometer,
  OrderStatePill,
  ReadinessRing,
  RiskPill,
  ShiftClock,
  StackLight,
  WeatherSourceBadge,
} from '../../components/domain'
import {
  Button,
  Chip,
  Field,
  Frame,
  Icon,
  Kbd,
  Nameplate,
  Segmented,
  Skeleton,
  Slider,
  Stamp,
  Table,
  Tabs,
  Toggle,
  Toast,
  Tooltip,
} from '../../components/primitives'
import { TitleBlock } from '../../components/TitleBlock'

const riskLevels = ['LOW', 'MODERATE', 'HIGH', 'SEVERE']
const orderStates = ['ON_TRACK', 'AT_RISK', 'LATE']
const backupStates = ['READY', 'STALE', 'APPROVAL_PENDING', 'ASSESSMENT_IN_PROGRESS', 'POTENTIAL_MATCH', 'UNAVAILABLE_EXPIRED']
const fallbackLevels = ['READY', 'POTENTIAL_ONLY', 'NONE']
const confidenceLevels = ['HIGH', 'MEDIUM', 'LOW', 'MISSING', 'CONFIRMED']

export default function ComponentKit() {
  const [windowValue, setWindowValue] = useState(48)
  const [tab, setTab] = useState('status')
  const [enabled, setEnabled] = useState(true)
  const [slider, setSlider] = useState(36)
  const [toast, setToast] = useState(true)

  return (
    <div className="f0-shell">
      <header className="f0-status-strip">
        <a className="f0-brand" href="/app">RELAY</a>
        <div className="f0-factory">F1 · Component Library</div>
        <div className="f0-status-meta"><DataLabelBadge /><StackLight exposure="HIGH" readiness={54} freshness="replay" /></div>
      </header>
      <main className="f0-content relay-kit">
        <div className="f0-kicker">VISUAL REGRESSION · HIDDEN ROUTE</div>
        <h1>Component Kit</h1>
        <p>Shared primitives and status variants. This route is for visual QA; it is not part of app navigation.</p>

        <Frame className="relay-kit__section">
          <h2>Controls</h2>
          <div className="relay-kit__row">
            <Button>Primary action</Button><Button variant="secondary">Secondary</Button><Button variant="ghost">Ghost</Button>
            <Button loading>Loading</Button><Button disabled>Disabled</Button>
          </div>
          <div className="relay-kit__row">
            <Segmented label="Window" value={windowValue} onChange={setWindowValue} options={[24, 48, 72]} />
            <Tabs label="Kit tabs" value={tab} onChange={setTab} tabs={[{ value: 'status', label: 'Status' }, { value: 'forms', label: 'Forms' }]} />
            <Toggle checked={enabled} onChange={setEnabled} label="Projector mode" />
          </div>
          <div className="relay-kit__row">
            <Slider label="Onset" min={0} max={72} value={slider} onChange={setSlider} />
            <Field label="Order ID" defaultValue="ord_102" hint="Nameplate IDs use mono type." />
            <Tooltip label="Example tooltip"><Chip tone="sky">Hover detail</Chip></Tooltip>
          </div>
          <div className="relay-kit__row">
            <Stamp>CONFIRMED</Stamp><Nameplate>fac_oragadam</Nameplate><Kbd>Ctrl K</Kbd>
            <Icon name="factory" label="Factory icon" /><Icon name="grinder" label="Grinder icon" />
          </div>
          <div className="relay-kit__row">
            <Skeleton lines={3} className="relay-kit__skeleton" />
            {toast && <Toast tone="warning" onDismiss={() => setToast(false)}>Using saved snapshot, not live.</Toast>}
          </div>
          <Table
            caption="Sample order rows"
            columns={[
              { key: 'id', label: 'Order', render: (row) => <Nameplate>{row.id}</Nameplate> },
              { key: 'value', label: 'Value', render: (row) => <Money value={row.value} /> },
              { key: 'state', label: 'State', render: (row) => <OrderStatePill value={row.state} /> },
            ]}
            rows={[
              { id: 'ord_102', value: 850000, state: 'AT_RISK' },
              { id: 'ord_107', value: 420000, state: 'ON_TRACK' },
            ]}
          />
        </Frame>

        <Frame className="relay-kit__section">
          <h2>Risk, order, fallback</h2>
          <div className="relay-kit__grid">
            {riskLevels.map((value) => <RiskPill key={value} value={value} />)}
            {orderStates.map((value) => <OrderStatePill key={value} value={value} />)}
            {fallbackLevels.map((value) => <FallbackShield key={value} value={value} />)}
          </div>
          <h2>Backup statuses</h2>
          <div className="relay-kit__grid">
            {backupStates.map((value) => <BackupStatusPill key={value} value={value} />)}
            <BackupStatusPill value="READY" excludedReason="SAME_HAZARD_ZONE" />
          </div>
          <h2>Confidence and data sources</h2>
          <div className="relay-kit__grid">
            {confidenceLevels.map((value) => <ConfidenceBars key={value} value={value} />)}
            <WeatherSourceBadge source="live" />
            <WeatherSourceBadge source="cache" degraded />
            <WeatherSourceBadge source="replay" />
            <WeatherSourceBadge source="synthetic" degraded />
          </div>
        </Frame>

        <Frame className="relay-kit__section">
          <h2>Domain primitives</h2>
          <div className="relay-kit__row">
            <ReadinessRing score={54} weighted={53.9} />
            <StackLight exposure="SEVERE" readiness={54} freshness="replay" />
            <ShiftClock time="04:53" />
            <DimensionLine value="242 mm" label="max 24 h" />
            <Money value={2_150_000} />
            <Odometer value={53.9} decimals={1} suffix="pts" />
          </div>
          <AlertBanner level="SEVERE" headline="Heavy rain in 23 h: review exposed orders." onset={23} action="Start recovery" />
          <div className="relay-kit__row">
            <CandidateCard candidate={{ name: 'Sample Components (Oragadam)', status: 'READY', effective_status: 'READY', filters: [] }} />
            <CandidateCard candidate={{ name: 'Sample Precision Works', status: 'READY', effective_status: 'READY', excluded: true, exclusion_reason: 'SAME_HAZARD_ZONE' }} />
          </div>
        </Frame>
      </main>
      <TitleBlock sheet="KIT / F1" />
    </div>
  )
}
