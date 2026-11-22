import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { apiRequest } from '../../api/client'
import { FACTORY_ID } from '../../api/hooks/useDeskData'
import { BackupStatusPill, ReadinessRing } from '../../components/domain'
import { Button, Frame, Nameplate, Segmented, Skeleton, Stamp, Toast } from '../../components/primitives'
import { backupStatusLabel, exclusionReasonLabel, readinessReasonLabel } from '../../lib/status'
import { useUiStore } from '../../store/ui'

const CHECKS = [
  'TECH_ASSESSMENT_DONE',
  'SAMPLE_APPROVED',
  'TERMS_AGREED',
  'CAPACITY_RECONFIRMED',
  'CUSTOMER_APPROVED',
]
const CHECK_LABELS = {
  TECH_ASSESSMENT_DONE: 'Technical assessment',
  SAMPLE_APPROVED: 'First-article sample approved',
  TERMS_AGREED: 'Commercial terms agreed',
  CAPACITY_RECONFIRMED: 'Capacity reconfirmed',
  CUSTOMER_APPROVED: 'Customer approved',
}

export default function Partners() {
  const queryClient = useQueryClient()
  const snapshotMode = useUiStore((state) => state.snapshotMode)
  const [windowHours, setWindowHours] = useState(48)
  const [selectedPartnerId, setSelectedPartnerId] = useState(null)
  const [actionToRun, setActionToRun] = useState(null)
  const [actionError, setActionError] = useState(null)
  const [detailError, setDetailError] = useState(null)

  const factories = useQuery({
    queryKey: ['factories'],
    queryFn: () => apiRequest('/factories'),
    staleTime: 30_000,
  })
  const relationships = useQuery({
    queryKey: ['relationships', FACTORY_ID],
    queryFn: () => apiRequest(`/factories/${FACTORY_ID}/relationships`),
    staleTime: 15_000,
  })
  const readiness = useQuery({
    queryKey: ['readiness', FACTORY_ID],
    queryFn: () => apiRequest(`/readiness/${FACTORY_ID}`),
    staleTime: 15_000,
  })
  const actions = useQuery({
    queryKey: ['readiness', FACTORY_ID, 'actions'],
    queryFn: () => apiRequest(`/readiness/${FACTORY_ID}/actions`),
    staleTime: 15_000,
  })
  const history = useQuery({
    queryKey: ['readiness', FACTORY_ID, 'history'],
    queryFn: () => apiRequest(`/readiness/${FACTORY_ID}/history`),
    staleTime: 15_000,
  })
  const matching = useQuery({
    queryKey: ['matching', 'hero-order', FACTORY_ID],
    queryFn: () => apiRequest('/matching/search', { method: 'POST', body: JSON.stringify({ order_id: 'ord_102' }) }),
    staleTime: 30_000,
  })

  const partners = useMemo(() => {
    const factoryList = factories.data?.items || []
    const relationshipsList = relationships.data || []
    const relationshipByPartner = new Map(relationshipsList.map((item) => [item.partner_id, item]))
    const exclusionByPartner = new Map((matching.data?.candidates || [])
      .filter((candidate) => candidate.excluded)
      .map((candidate) => [candidate.partner_id, candidate.exclusion_reason]))
    return factoryList
      .filter((factory) => factory.role === 'PARTNER')
      .map((factory) => ({
        ...factory,
        relationship: relationshipByPartner.get(factory.id) || null,
        excluded: exclusionByPartner.has(factory.id),
        exclusionReason: exclusionByPartner.get(factory.id),
      }))
      .sort((a, b) => (a.relationship?.effective_status || 'POTENTIAL_MATCH').localeCompare(b.relationship?.effective_status || 'POTENTIAL_MATCH'))
  }, [factories.data, relationships.data, matching.data])

  const headline = readiness.data?.windows?.find((item) => item.window_hours === windowHours)
    || readiness.data?.windows?.find((item) => item.window_hours === 48)
  const selected = partners.find((partner) => partner.id === selectedPartnerId)
  const counts = useMemo(() => ({
    ready: partners.filter((partner) => !partner.excluded && partner.relationship?.effective_status === 'READY').length,
    stale: partners.filter((partner) => partner.relationship?.effective_status === 'STALE').length,
    pending: partners.filter((partner) => partner.relationship?.effective_status === 'APPROVAL_PENDING').length,
    excluded: partners.filter((partner) => partner.excluded).length,
  }), [partners])

  const refreshRelated = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['relationships', FACTORY_ID] }),
      queryClient.invalidateQueries({ queryKey: ['readiness', FACTORY_ID] }),
      queryClient.invalidateQueries({ queryKey: ['dashboard', FACTORY_ID] }),
      queryClient.invalidateQueries({ queryKey: ['matching', 'hero-order', FACTORY_ID] }),
    ])
  }

  const completeCheck = useMutation({
    mutationFn: ({ relationshipId, key }) => apiRequest(`/relationships/${relationshipId}/checks/${key}/complete`, { method: 'POST' }),
    onSuccess: refreshRelated,
    onError: (error) => setDetailError(error),
  })

  const setStatus = useMutation({
    mutationFn: ({ relationshipId, status }) => apiRequest(`/relationships/${relationshipId}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status }),
    }),
    onSuccess: async () => {
      setDetailError(null)
      await refreshRelated()
    },
    onError: (error) => setDetailError(error),
  })

  const reconfirm = useMutation({
    mutationFn: (relationshipId) => apiRequest(`/relationships/${relationshipId}/reconfirm`, { method: 'POST' }),
    onSuccess: refreshRelated,
    onError: (error) => setDetailError(error),
  })

  const runAction = async () => {
    if (!actionToRun) return
    setActionError(null)
    try {
      const partner = partners.find((item) => item.id === actionToRun.partner_id)
      const relationship = partner?.relationship
      if (!relationship) throw new Error('No backup relationship exists for this partner.')
      if (relationship.status === 'READY') {
        await reconfirm.mutateAsync(relationship.id)
      } else {
        const pendingChecks = (relationship.checks || []).filter((check) => !check.done)
        for (const check of pendingChecks) {
          await completeCheck.mutateAsync({ relationshipId: relationship.id, key: check.key })
        }
        await setStatus.mutateAsync({ relationshipId: relationship.id, status: 'READY' })
      }
      setActionToRun(null)
      await refreshRelated()
    } catch (error) {
      setActionError(error.message || 'Could not complete the action.')
    }
  }

  if (factories.isLoading || relationships.isLoading || readiness.isLoading) {
    return <main className="partners-page"><div className="f0-kicker">BACKUP NETWORK</div><h1>PARTNERS</h1><Skeleton lines={7} /></main>
  }

  if (factories.isError || relationships.isError || readiness.isError) {
    const error = factories.error || relationships.error || readiness.error
    return (
      <main className="partners-page"><Frame className="partners-error">
        <Nameplate>{error.code || 'CONNECTION_ERROR'}</Nameplate><p>{error.message}</p>
        <Button variant="secondary" onClick={() => { factories.refetch(); relationships.refetch(); readiness.refetch() }}>Retry</Button>
      </Frame></main>
    )
  }

  return (
    <main className="partners-page">
      <header className="partners-heading">
        <div><span className="f0-kicker">BACKUP NETWORK · SAMPLE WORLD</span><h1>PARTNERS & READINESS</h1></div>
        <Nameplate>fac_owner</Nameplate>
      </header>

      {actionError && <Toast tone="warning">{actionError}</Toast>}
      {detailError && (
        <Toast tone="warning">
          {detailError.message}
          {detailError.details?.missing_checks?.length > 0 && ` · Missing: ${detailError.details.missing_checks.join(', ')}`}
        </Toast>
      )}

      <Frame className="partners-circuit-frame">
        <header className="partners-section-heading">
          <div><span className="f0-kicker">BACKUP NETWORK</span><h2>Who can cover your work</h2></div>
          <div className="partners-circuit-legend"><span className="is-ready">━ Ready</span><span className="is-pending">┄ Pending</span><span className="is-excluded">░ Excluded</span></div>
        </header>
        <RelayCircuit partners={partners} onSelect={setSelectedPartnerId} />
      </Frame>

      <section className="partners-panels">
        <Frame className="partners-readiness">
          <header className="partners-section-heading">
            <div><span className="f0-kicker">COVERED SHARE</span><h2>Readiness of your parts</h2></div>
            <Segmented label="Readiness window" value={windowHours} onChange={setWindowHours} options={[24, 48, 72]} />
          </header>
          {headline && (
            <button type="button" className="partners-readiness__ring" onClick={() => setSelectedPartnerId(null)}>
              <ReadinessRing score={headline.score} weighted={headline.weighted_score} size={172} />
              <span>OPEN PART-BY-PART BREAKDOWN · {windowHours} h</span>
            </button>
          )}
          <div className="partners-readiness__windows">
            {(readiness.data?.windows || []).map((window) => (
              <div key={window.window_hours}><small>{window.window_hours} h</small><b>{window.weighted_score}</b></div>
            ))}
          </div>
          {readiness.data?.breakdown && (
            <div className="partners-readiness__breakdown">
              {readiness.data.breakdown.map((item) => (
                <div key={item.part_id}>
                  <span>{item.covered ? '✓' : '░'}</span><b>{item.part_name}</b>
                  <small>{item.covered ? `Covered by ${partnerName(partners, item.covered_by)}` : readinessReasonLabel(item.reason)}</small>
                </div>
              ))}
            </div>
          )}
        </Frame>

        <Frame className="partners-review">
          <header className="partners-section-heading"><div><span className="f0-kicker">NEEDS ATTENTION</span><h2>Partner confirmations</h2></div></header>
          <div className="partners-counts">
            <span><b>{counts.ready}</b> ready</span><span><b>{counts.pending}</b> pending</span><span><b>{counts.stale}</b> needs reconfirming</span>
          </div>
          <div className="partners-review__list">
            {(readiness.data?.review || []).map((item) => (
              <button type="button" key={item.relationship_id} onClick={() => setSelectedPartnerId(item.partner_id)}>
                <span>{item.effective_status === 'STALE' ? '◷' : item.expiring ? '⌛' : '✓'}</span>
                <span><b>{item.partner_name}</b><small>{backupStatusLabel(item.effective_status)} · confirmed {item.days_since_confirm ?? '—'} days ago{item.expiring ? ' · expiring soon' : ''}</small></span>
                <span className="partners-review__action">REVIEW →</span>
              </button>
            ))}
            {!(readiness.data?.review || []).length && <p>No stale or expiring READY relationships.</p>}
          </div>
          {selected && <PartnerDrawer
            partner={selected}
            error={detailError}
            onClose={() => { setSelectedPartnerId(null); setDetailError(null) }}
            onComplete={(key) => completeCheck.mutate({ relationshipId: selected.relationship.id, key })}
            onReconfirm={() => reconfirm.mutate(selected.relationship.id)}
             onSetStatus={(status) => setStatus.mutate({ relationshipId: selected.relationship.id, status })}
             busy={completeCheck.isPending || reconfirm.isPending || setStatus.isPending}
             readOnly={snapshotMode}
          />}
        </Frame>

        <Frame className="partners-actions">
          <header className="partners-section-heading"><div><span className="f0-kicker">WHAT WOULD RAISE YOUR SCORE</span><h2>Next best actions</h2></div></header>
          {actions.isLoading ? <Skeleton lines={3} /> : actions.isError ? (
            <InlineError message={actions.error.message} onRetry={() => actions.refetch()} />
          ) : actions.data?.actions?.length ? actions.data.actions.slice(0, 5).map((action) => (
            <div className="partners-action" key={action.relationship_id}>
              <div><strong>{action.label}</strong><small>{action.current_score} → {action.projected_score}</small></div>
              <b>+{action.uplift_points} pts</b>
              <Button variant="secondary" size="small" disabled={snapshotMode} onClick={() => setActionToRun(action)}>Do it</Button>
            </div>
          )) : <p>No positive-uplift actions at this window.</p>}
          <div className="partners-history">
            <div className="partners-section-heading"><div><span className="f0-kicker">SCORE HISTORY</span><h2>How your readiness changed</h2></div></div>
            {history.isLoading ? <Skeleton lines={3} /> : history.isError ? <InlineError message={history.error.message} onRetry={() => history.refetch()} />
              : <ReadinessHistory points={history.data?.points || []} />}
          </div>
        </Frame>
      </section>

      {actionToRun && <ConfirmAction action={actionToRun} onCancel={() => setActionToRun(null)} onConfirm={runAction} loading={completeCheck.isPending || reconfirm.isPending || setStatus.isPending} readOnly={snapshotMode} />}
      <div className="partners-caveat">Matches are candidates, not approved backups. Risk is an indicator, not a prediction.</div>
    </main>
  )
}

function partnerName(partners, partnerId) {
  return partners.find((item) => item.id === partnerId)?.name || partnerId || '—'
}

function RelayCircuit({ partners, onSelect }) {
  return (
    <div className="relay-network">
      <div className="relay-network__owner"><Nameplate>OWNER · Sample Precision Components</Nameplate><i /></div>
      <div className="relay-network__partners">
        {partners.map((partner) => {
          const status = partner.relationship?.effective_status || 'POTENTIAL_MATCH'
          const className = partner.excluded ? 'excluded' : status === 'READY' ? 'ready' : status === 'STALE' || status === 'APPROVAL_PENDING' ? 'pending' : 'potential'
          return (
            <button className={`relay-network__partner is-${className}`} type="button" key={partner.id} onClick={() => onSelect(partner.id)}>
              <i aria-hidden="true">{className === 'ready' ? '●' : className === 'excluded' ? '░' : className === 'pending' ? '◷' : '○'}</i>
              <span><b>{partner.name}</b><small>{partner.excluded ? `Excluded · ${exclusionReasonLabel(partner.exclusionReason)}` : backupStatusLabel(status)}</small></span>
              <BackupStatusPill value={status} excludedReason={partner.exclusionReason} />
            </button>
          )
        })}
      </div>
    </div>
  )
}

function PartnerDrawer({ partner, error, onClose, onComplete, onReconfirm, onSetStatus, busy, readOnly = false }) {
  const relationship = partner.relationship
  if (!relationship) {
    return <aside className="partners-drawer"><Button variant="ghost" size="small" onClick={onClose}>Close</Button><p>No relationship record exists; candidate is POTENTIAL_MATCH.</p></aside>
  }
  const checks = relationship.checks || []
  return (
    <aside className="partners-drawer">
      <header><div><span className="f0-kicker">PARTNER NAMEPLATE</span><h3>{partner.name}</h3></div><Button variant="ghost" size="small" onClick={onClose}>Close</Button></header>
      <div className="partners-drawer__profile">
        <Nameplate>{partner.id}</Nameplate><span>{partner.cluster_id}</span><span>{partner.materials_handled?.join(' · ')}</span>
      </div>
      <BackupStatusPill value={relationship.effective_status} />
      <h4>Checks before this partner is Ready</h4>
      <ul className="partners-checks">
        {CHECKS.map((key) => {
          const check = checks.find((item) => item.key === key)
          return (
            <li key={key}>
              <span className={check?.done ? 'is-done' : 'is-pending'}>{check?.done ? '✓' : '○'}</span>
              <span>{CHECK_LABELS[key]}</span>
              {!check?.done && <Button variant="ghost" size="small" disabled={readOnly || busy} onClick={() => onComplete(key)}>{readOnly ? 'Read-only' : 'Complete'}</Button>}
            </li>
          )
        })}
      </ul>
      {error?.details?.missing_checks?.length > 0 && (
        <div className="partners-guard-error"><Stamp tone="gold">CANNOT SET READY</Stamp><p>Missing: {error.details.missing_checks.join(', ')}</p></div>
      )}
      <div className="partners-drawer__actions">
        <label>Set status<select value={partner.relationship.status} disabled={readOnly || busy} onChange={(event) => onSetStatus(event.target.value)}>
          {['POTENTIAL_MATCH', 'ASSESSMENT_IN_PROGRESS', 'APPROVAL_PENDING', 'READY', 'UNAVAILABLE_EXPIRED'].map((option) => <option key={option} value={option}>{backupStatusLabel(option)}</option>)}
        </select></label>
        <Button variant="secondary" disabled={readOnly || busy || !partner.relationship.last_confirmed_at} onClick={onReconfirm}>Reconfirm</Button>
      </div>
    </aside>
  )
}

function ConfirmAction({ action, onCancel, onConfirm, loading, readOnly = false }) {
  return (
    <div className="partners-confirm-overlay" onMouseDown={(event) => event.target === event.currentTarget && onCancel()}>
      <section className="partners-confirm" role="dialog" aria-modal="true" aria-label="Confirm readiness action">
        <span className="f0-kicker">COUNTERFACTUAL ACTION · {action.uplift_points > 0 ? `+${action.uplift_points}` : ''} PTS</span>
        <h2>{action.label}</h2>
        <p>Current weighted score {action.current_score} · projected {action.projected_score}. The relationship and readiness history will be updated.</p>
        <div><Button variant="ghost" disabled={loading} onClick={onCancel}>Cancel</Button><Button disabled={readOnly} loading={loading} onClick={onConfirm}>Do it</Button></div>
      </section>
    </div>
  )
}

function ReadinessHistory({ points }) {
  if (!points.length) return <p>No readiness snapshots yet. The score history starts after the first computation.</p>
  const series = points.map((point) => ({
    ...point,
    name: new Date(point.computed_at).toLocaleString('en-GB', {
      timeZone: 'Asia/Kolkata', day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit',
    }),
    weighted_score: point.weighted_score,
  }))
  return (
    <div className="partners-history__chart">
      <ResponsiveContainer width="100%" height={180}>
        <LineChart data={series}>
          <XAxis dataKey="name" stroke="var(--c-pale)" tick={{ fill: 'var(--c-pale)', fontSize: 9 }} />
          <YAxis domain={[0, 100]} stroke="var(--c-pale)" tick={{ fill: 'var(--c-pale)', fontSize: 9 }} />
          <Tooltip contentStyle={{ background: 'var(--c-midnight)', border: '1px solid var(--c-sky)', color: 'var(--c-cream)' }} />
          <Line dataKey="weighted_score" type="stepAfter" stroke="var(--c-sky)" strokeWidth={2} dot={{ fill: 'var(--c-sun)', r: 3 }} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

function InlineError({ message, onRetry }) {
  return <div className="partners-inline-error" role="alert"><span>{message}</span><Button variant="ghost" size="small" onClick={onRetry}>Retry</Button></div>
}
