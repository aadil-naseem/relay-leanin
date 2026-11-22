import { Button, Nameplate } from '../../components/primitives'
import { useRelayNavigate } from '../../app/navigation'
import './system.css'

export function SystemNotFound() {
  const navigate = useRelayNavigate()

  return (
    <main className="system-page system-not-found">
      <div className="system-contact-glyph" role="img" aria-label="Open relay contact">
        <svg viewBox="0 0 240 150" aria-hidden="true">
          <path d="M14 75h62m0-25v50m0-50 60 25m25 0h65" />
          <circle cx="76" cy="75" r="5" />
          <circle cx="161" cy="75" r="5" />
          <path className="system-contact-glyph__spark" d="m112 25 13-15m9 20 18-14" />
        </svg>
      </div>
      <span className="f0-kicker">ROUTE ERROR · 404</span>
      <h1>LINE NOT FOUND</h1>
      <p>This route is not connected. The sample world is unchanged.</p>
      <Nameplate>CONTACT OPEN · NO ROUTE</Nameplate>
      <Button variant="secondary" onClick={() => navigate('/app')}>Back to Desk</Button>
    </main>
  )
}

export function BackendUnavailable({ error, retrying = false, onRetry, onOpenSnapshot, snapshotCapturedAt }) {
  return (
    <main className="system-page system-offline" role="alert">
      <div className="system-offline__layout">
        <div className="system-contact-glyph system-contact-glyph--offline" aria-hidden="true">
          <svg viewBox="0 0 240 150">
            <path d="M14 75h62m0-25v50m0-50 60 25m25 0h65" />
            <circle cx="76" cy="75" r="5" />
            <circle cx="161" cy="75" r="5" />
          </svg>
        </div>
        <span className="f0-kicker">SYSTEM · CONNECTION LOST</span>
        <h1>CAN’T REACH THE SERVER</h1>
        <p className="system-offline__message">
          RELAY can’t load live data right now. Retry the connection or continue with a saved replay pack if one is available.
        </p>
        <Nameplate>{error?.code || 'BACKEND_UNREACHABLE'}</Nameplate>
        <div className="system-offline__actions">
          <Button loading={retrying} onClick={onRetry}>Retry connection</Button>
          <Button variant="secondary" disabled={!onOpenSnapshot} onClick={onOpenSnapshot}>
            Open saved snapshot
          </Button>
        </div>
        <p className="system-offline__snapshot" role="status">
          Read-only replay captured {snapshotCapturedAt ? new Date(snapshotCapturedAt).toLocaleString() : 'from the seeded replay'}.
          Live data and write actions are unavailable in snapshot mode.
        </p>
      </div>
    </main>
  )
}
