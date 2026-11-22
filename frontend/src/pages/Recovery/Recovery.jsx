import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import { apiRequest } from '../../api/client'
import { BackupStatusPill, CalcLog } from '../../components/domain'
import { PaperSheet } from '../../components/domain'
import { Button, Frame, Nameplate, Skeleton, Stamp, Toast } from '../../components/primitives'
import { hazardName, orderLabel, recoveryStatusLabel, routeStepLabel } from '../../lib/status'
import { useRelayNavigate } from '../../app/navigation'
import { useUiStore } from '../../store/ui'

const FILTER_LABELS = {
  process: 'Process',
  material: 'Material',
  tolerance: 'Tolerance',
  envelope: 'Envelope',
  capacity: 'Capacity',
  lead_time: 'Lead time',
}
const NO_CANDIDATES = []

export default function Recovery() {
  const navigate = useRelayNavigate()
  const snapshotMode = useUiStore((state) => state.snapshotMode)
  const { id } = useParams()
  const queryClient = useQueryClient()
  const [candidateToSelect, setCandidateToSelect] = useState(null)
  const [actionError, setActionError] = useState(null)
  const [traceOpen, setTraceOpen] = useState(false)

  const request = useQuery({
    queryKey: ['recovery-request', id],
    queryFn: () => apiRequest(`/recovery-requests/${id}`),
    enabled: Boolean(id),
    staleTime: 15_000,
  })
  const orderBundle = useQuery({
    queryKey: ['recovery-order', request.data?.order_id],
    queryFn: async () => {
      const [orders, parts] = await Promise.all([
        apiRequest(`/factories/${request.data.factory_id}/orders`),
        apiRequest(`/factories/${request.data.factory_id}/parts`),
      ])
      const order = orders.items.find((item) => item.id === request.data.order_id)
      const part = parts.items.find((item) => item.id === order?.part_id)
      return { order, part }
    },
    enabled: Boolean(request.data),
  })
  const stress = useQuery({
    queryKey: ['stress-test', request.data?.stress_test_id],
    queryFn: () => apiRequest(`/stress-tests/${request.data.stress_test_id}`),
    enabled: Boolean(request.data?.stress_test_id),
    staleTime: 30_000,
  })
  const matching = useQuery({
    queryKey: ['matching', request.data?.order_id, request.data?.stress_test_id],
    queryFn: async () => {
      const scenario = stress.data
        ? { hazard: stress.data.hazard, affected_sites: stress.data.affected_sites }
        : undefined
      return apiRequest('/matching/search', {
        method: 'POST',
        body: JSON.stringify({ order_id: request.data.order_id, scenario }),
      })
    },
    enabled: Boolean(request.data) && (!request.data.stress_test_id || Boolean(stress.data)),
    staleTime: 15_000,
  })
  const tracking = useQuery({
    queryKey: ['recovery-tracking', id],
    queryFn: () => apiRequest(`/recovery-requests/${id}/tracking`),
    enabled: Boolean(id && request.data?.selected_partner_id),
    staleTime: 0,
  })
  const handover = useQuery({
    queryKey: ['recovery-handover', id, request.data?.selected_partner_id],
    queryFn: () => apiRequest(`/recovery-requests/${id}/handover`),
    enabled: Boolean(id && request.data?.selected_partner_id),
    staleTime: 30_000,
  })

  const selectPartner = useMutation({
    mutationFn: (partnerId) => apiRequest(`/recovery-requests/${id}/select-partner`, {
      method: 'POST',
      body: JSON.stringify({ partner_id: partnerId }),
    }),
    onSuccess: async () => {
      setCandidateToSelect(null)
      setActionError(null)
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['recovery-request', id] }),
        queryClient.invalidateQueries({ queryKey: ['recovery-tracking', id] }),
        queryClient.invalidateQueries({ queryKey: ['recovery-handover', id] }),
      ])
    },
    onError: (error) => setActionError(error.message),
  })

  const advance = useMutation({
    mutationFn: () => apiRequest(`/recovery-requests/${id}/tracking/advance`, { method: 'POST' }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['recovery-tracking', id] })
    },
    onError: (error) => setActionError(error.message),
  })

  const candidates = matching.data?.candidates || NO_CANDIDATES
  const grouped = useMemo(() => ({
    ready: candidates.filter((candidate) => !candidate.excluded && candidate.effective_status === 'READY'),
    pending: candidates.filter((candidate) => !candidate.excluded && candidate.status === 'APPROVAL_PENDING'),
    excluded: candidates.filter((candidate) => candidate.excluded),
    other: candidates.filter((candidate) => !candidate.excluded && !['READY', 'APPROVAL_PENDING'].includes(candidate.effective_status)),
  }), [candidates])

  if (!id) return <RecoveryEntry onGo={navigate} />
  if (request.isLoading) return <main className="recovery-page"><div className="f0-kicker">RECOVERY HANDOVER</div><h1>RECOVERY</h1><Skeleton lines={6} /></main>
  if (request.isError) {
    return (
      <main className="recovery-page">
        <Frame className="recovery-error"><Nameplate>{request.error.code || 'NOT_FOUND'}</Nameplate><p>{request.error.message}</p><Button variant="secondary" onClick={() => request.refetch()}>Retry</Button></Frame>
      </main>
    )
  }

  const detail = orderBundle.data
  const allSteps = tracking.data?.steps || []
  const pendingStep = allSteps.find((step) => step.state === 'PENDING')
  const completedSteps = allSteps.filter((step) => step.state === 'DONE').length
  const activationNote = request.data.activation_note || 'Activation is subject to human, customer and contractual approvals outside this software.'

  return (
    <main className="recovery-page">
      <header className="recovery-heading">
        <div><span className="f0-kicker">HANDOFF · SAMPLE WORLD</span><h1>RECOVERY</h1></div>
        <div className="recovery-heading__meta"><Nameplate>{request.data.id}</Nameplate><Stamp tone="gold">{request.data.data_label}</Stamp></div>
      </header>

      <Frame className="recovery-request-summary">
        <div>
          <span className="f0-kicker">REQUEST · {recoveryStatusLabel(request.data.status).toUpperCase()}</span>
          <h2>{stress.data ? `${hazardName(stress.data.hazard)} · ${stress.data.params?.scope?.type || 'scenario'}` : 'Manual recovery request'}</h2>
        </div>
        <div className="recovery-request-summary__facts">
          <Nameplate>{orderLabel(request.data.order_id)}</Nameplate>
          <span>{detail?.part?.name || 'Loading order…'} × {detail?.order?.qty ?? '—'}</span>
          <span>Due {detail?.order?.due_at ? new Date(detail.order.due_at).toLocaleString('en-GB', { timeZone: 'Asia/Kolkata', dateStyle: 'medium' }) : '—'}</span>
          {stress.data?.affected_sites?.length > 0 && <span>Sites · {stress.data.affected_sites.join(', ')}</span>}
        </div>
        <p className="recovery-approval-note">{activationNote}</p>
      </Frame>

      {actionError && <Toast tone="warning">{actionError}</Toast>}
      {(matching.isError || handover.isError || tracking.isError) && (
        <Toast tone="warning">Some recovery details could not be loaded. Retry the affected panel.</Toast>
      )}

      <section className="recovery-candidate-section">
        <header className="recovery-section-heading">
          <div><span className="f0-kicker">M6 · SCENARIO-AWARE MATCHES</span><h2>Backup candidates</h2></div>
          <p>A match is a candidate, not an approved backup.</p>
        </header>
        {matching.isLoading ? <Skeleton lines={4} /> : (
          <div className="recovery-candidate-columns">
            <CandidateColumn title="READY" tone="sky" items={grouped.ready} selectedId={request.data.selected_partner_id} onSelect={snapshotMode ? undefined : setCandidateToSelect} readOnly={snapshotMode} />
            <CandidateColumn title="APPROVAL PENDING" tone="pale" items={grouped.pending} selectedId={request.data.selected_partner_id} onSelect={snapshotMode ? undefined : setCandidateToSelect} readOnly={snapshotMode} />
            <CandidateColumn title="EXCLUDED" tone="sun" items={grouped.excluded} selectedId={request.data.selected_partner_id} onSelect={snapshotMode ? undefined : setCandidateToSelect} readOnly={snapshotMode} />
            {grouped.other.length > 0 && <CandidateColumn title="OTHER CANDIDATES" tone="hair" items={grouped.other} selectedId={request.data.selected_partner_id} onSelect={snapshotMode ? undefined : setCandidateToSelect} readOnly={snapshotMode} />}
          </div>
        )}
      </section>

      {request.data.selected_partner_id && (
        <section className="recovery-fulfilment">
          <Frame className="recovery-handover">
            <header className="recovery-section-heading">
              <div><span className="f0-kicker">M9 · PREPARED FROM AUTHORISED DATA</span><h2>Handover pack</h2></div>
              <Stamp tone="gold">{handover.data?.data_label || 'SIMULATED SAMPLE'}</Stamp>
            </header>
            {handover.isLoading ? <Skeleton lines={5} /> : handover.data ? (
              <PaperSheet title={handover.data.job_requirements.job} watermark="SIMULATED SAMPLE">
                <div className="recovery-handover__facts">
                  <p><b>Material</b><span>{handover.data.job_requirements.material}</span></p>
                  <p><b>Quantity</b><span>{handover.data.quantity}</span></p>
                  <p><b>Deadline</b><span>{new Date(handover.data.deadline).toLocaleString('en-GB', { timeZone: 'Asia/Kolkata', dateStyle: 'medium' })}</span></p>
                  <p><b>Documents</b><span>{handover.data.authorised_documents.join(' · ')}</span></p>
                </div>
                <h3>Inspection checklist</h3>
                <ul>{handover.data.inspection_checklist.map((item) => <li key={item}>{item}</li>)}</ul>
                <h3>Required approvals</h3>
                <ul>{handover.data.required_approvals.map((item) => <li key={item}>{item}</li>)}</ul>
                <h3>Responsibilities</h3>
                <ul>{handover.data.responsibilities.map((item) => <li key={`${item.party}-${item.responsibility}`}><b>{item.party}:</b> {item.responsibility}</li>)}</ul>
                <h3>Simulated milestones</h3>
                <ul>{handover.data.milestones.map((item) => <li key={item.step_key}>{routeStepLabel(item.step_key)} · T+{item.target_offset_hours} h</li>)}</ul>
                <p className="recovery-contacts-note">Contact details are not included in the current handover API response.</p>
                <details className="recovery-pack-text"><summary>Printable pack</summary><pre>{handover.data.text}</pre></details>
                <p className="recovery-approval-note">{activationNote}</p>
              </PaperSheet>
            ) : null}
          </Frame>

          <Frame className="recovery-tracking">
            <header className="recovery-section-heading">
              <div><span className="f0-kicker">M10 · SIMULATED TRACKING</span><h2>Route card</h2></div>
              <Nameplate>{completedSteps}/{allSteps.length || 7} COMPLETE</Nameplate>
            </header>
            {tracking.isLoading ? <Skeleton lines={5} /> : tracking.data && (
              <>
                <ol className="recovery-stepper">
                  {tracking.data.steps.map((step, index) => (
                    <li key={step.step_key} className={`${step.state === 'DONE' ? 'is-done' : ''} ${pendingStep?.step_key === step.step_key ? 'is-current' : ''}`}>
                      <span>{String(index + 1).padStart(2, '0')}</span><small>{routeStepLabel(step.step_key)}</small>
                    </li>
                  ))}
                </ol>
                <Button
                  variant="secondary"
                  disabled={snapshotMode || !pendingStep || advance.isPending}
                  loading={advance.isPending}
                  onClick={() => advance.mutate()}
                >
                  {snapshotMode ? 'Saved snapshot · read only' : pendingStep ? `Advance · ${routeStepLabel(pendingStep.step_key)}` : 'Simulated route complete'}
                </Button>
              </>
            )}
          </Frame>
        </section>
      )}

      {candidateToSelect && (
        <ConfirmSelection
          candidate={candidateToSelect}
          note={activationNote}
          loading={selectPartner.isPending}
          readOnly={snapshotMode}
          onCancel={() => setCandidateToSelect(null)}
          onConfirm={() => selectPartner.mutate(candidateToSelect.partner_id)}
        />
      )}
      {matching.data?.trace?.length > 0 && <Button className="recovery-calc-link" variant="ghost" size="small" onClick={() => setTraceOpen(true)}>How was this matched?</Button>}
      {traceOpen && <TraceDrawer trace={matching.data?.trace || []} onClose={() => setTraceOpen(false)} />}
    </main>
  )
}

function CandidateColumn({ title, tone, items, selectedId, onSelect, readOnly = false }) {
  return (
    <section className={`recovery-candidate-column recovery-candidate-column--${tone}`}>
      <h3>{title}<span>{items.length}</span></h3>
      {!items.length && <p className="recovery-candidate-column__empty">No candidates in this group.</p>}
      {items.map((candidate) => (
        <CandidateCard
          key={candidate.partner_id}
          candidate={candidate}
          selected={selectedId === candidate.partner_id}
          onSelect={!candidate.excluded ? onSelect : undefined}
          readOnly={readOnly}
        />
      ))}
    </section>
  )
}

function CandidateCard({ candidate, selected, onSelect, readOnly = false }) {
  const failed = (candidate.filters || []).filter((filter) => filter.result === 'FAIL')
  const passed = (candidate.filters || []).filter((filter) => filter.result === 'PASS')
  const unknown = (candidate.filters || []).filter((filter) => filter.result === 'UNKNOWN')
  const canSelect = !candidate.excluded && failed.length === 0 && Boolean(onSelect)

  return (
    <Frame className={`recovery-candidate-card ${candidate.excluded ? 'is-excluded' : ''} ${selected ? 'is-selected' : ''}`}>
      <header>
        <h4>{candidate.name}</h4>
        <BackupStatusPill value={candidate.effective_status || candidate.status} excludedReason={candidate.exclusion_reason && candidate.excluded ? candidate.exclusion_reason : null} />
      </header>
      <div className="recovery-candidate-card__facts">
        <Nameplate>{candidate.partner_id}</Nameplate>
        <span>{candidate.distance_km} km</span>
        {candidate.score != null && <b>{candidate.score.toFixed(1)} pts</b>}
      </div>
      {(passed.length > 0 || failed.length > 0 || unknown.length > 0) && (
        <div className="recovery-checks">
          <span className="f0-kicker">CHECKED · DECLARED PROFILE</span>
          {passed.map((filter) => <p className="is-pass" key={filter.key}><i>✓</i><b>{FILTER_LABELS[filter.key] || filter.key}</b><small>{filter.detail}</small></p>)}
          {failed.map((filter) => <p className="is-fail" key={filter.key}><i>×</i><b>{FILTER_LABELS[filter.key] || filter.key}</b><small>{filter.detail}</small></p>)}
          {unknown.length > 0 && <div className="recovery-checks__unknown">
            <span className="f0-kicker">UNKNOWN · VERIFY BEFORE ACTIVATION</span>
            {unknown.map((filter) => <p key={filter.key}><i>?</i><b>{FILTER_LABELS[filter.key] || filter.key}</b><small>{filter.detail}</small></p>)}
          </div>}
        </div>
      )}
      {!!candidate.unverified?.length && (
        <div className="recovery-unverified">
          <span className="f0-kicker">UNVERIFIED · CHECKS TO CLOSE</span>
          {candidate.unverified.slice(0, 3).map((item) => <small key={item}>○ {item}</small>)}
        </div>
      )}
      <p className="recovery-candidate-card__note">A match is a candidate, not an approved backup.</p>
      {candidate.excluded ? (
        <Button variant="ghost" size="small" disabled title={`Excluded: ${candidate.exclusion_reason}`}>Cannot select</Button>
      ) : (
        <Button variant={selected ? 'ghost' : 'secondary'} size="small" disabled={readOnly || !canSelect || selected} onClick={() => onSelect(candidate)}>
          {readOnly ? 'Read-only snapshot' : selected ? 'Selected' : canSelect ? 'Select partner' : 'Hard filters failed'}
        </Button>
      )}
    </Frame>
  )
}

function ConfirmSelection({ candidate, note, loading, onCancel, onConfirm, readOnly = false }) {
  return (
    <div className="recovery-confirm-overlay" onMouseDown={(event) => event.target === event.currentTarget && onCancel()}>
      <section className="recovery-confirm" role="dialog" aria-modal="true" aria-label="Confirm partner selection">
        <span className="f0-kicker">REQUEST ACTIVATION</span>
        <h2>Select {candidate.name}?</h2>
        <p>{note}</p>
        <div className="recovery-confirm__actions">
          <Button variant="ghost" disabled={loading} onClick={onCancel}>Cancel</Button>
          <Button disabled={readOnly} loading={loading} onClick={onConfirm}>Send recovery request</Button>
        </div>
      </section>
    </div>
  )
}

function TraceDrawer({ trace, onClose }) {
  return (
    <div className="whatif-overlay" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section className="whatif-trace" role="dialog" aria-modal="true" aria-label="Matching calculation log">
        <header><div><span className="f0-kicker">MATCHING TRACE</span><h2>Why these candidates?</h2></div><Button variant="ghost" size="small" onClick={onClose}>Close</Button></header>
        <CalcLog entries={trace} />
      </section>
    </div>
  )
}

function RecoveryEntry() {
  const navigate = useRelayNavigate()
  return (
    <main className="recovery-page">
      <Frame className="recovery-entry">
        <span className="f0-kicker">RECOVERY · PREFILLED FROM AN ALERT OR STRESS TEST</span>
        <h1>RECOVERY</h1>
        <p>Start from Desk or What-if to carry the alert, order and scenario into a recovery request.</p>
        <Button variant="secondary" onClick={() => navigate('/app')}>Back to Desk</Button>
      </Frame>
    </main>
  )
}
