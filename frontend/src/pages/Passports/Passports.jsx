import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useParams } from 'react-router-dom'
import { apiRequest } from '../../api/client'
import { ConfidenceBars, PaperSheet } from '../../components/domain'
import { Button, Field, Frame, Nameplate, Segmented, Stamp, Toast } from '../../components/primitives'
import { useUiStore } from '../../store/ui'
import { snapshotPassportId } from '../../api/snapshot'

const samples = [
  { id: 'pump_shaft', label: 'Pump shaft', filename: 'pump_shaft.png', pdf: 'pump_shaft.pdf' },
  { id: 'piston_rod', label: 'Piston rod', filename: 'piston_rod.png', pdf: 'piston_rod.pdf' },
  { id: 'valve_flange', label: 'Valve flange', filename: 'valve_flange.png', pdf: 'valve_flange.pdf' },
]

const steps = [
  'Drawing',
  'Review',
  'Confirm',
  'Redacted RFQ',
  'Share',
]

const fieldSpecs = [
  { key: 'part_name', label: 'Part name', type: 'text' },
  { key: 'drawing_no', label: 'Drawing number', type: 'text' },
  { key: 'revision', label: 'Revision', type: 'text' },
  { key: 'customer', label: 'Customer', type: 'text' },
  { key: 'quantity', label: 'Quantity', type: 'number' },
  { key: 'tightest_tolerance_mm', label: 'Tightest tolerance (mm)', type: 'number' },
  { key: 'general_tolerance_standard', label: 'General tolerance standard', type: 'text' },
  { key: 'surface_finish_ra_um', label: 'Surface finish Ra (µm)', type: 'number' },
  { key: 'envelope_mm', label: 'Envelope (mm)', type: 'number' },
  { key: 'heat_treatment', label: 'Heat treatment', type: 'text' },
  { key: 'coating', label: 'Coating', type: 'text' },
  { key: 'deadline', label: 'Deadline (ISO date/time)', type: 'text' },
]

export default function Passports() {
  const { id } = useParams()
  const snapshotMode = useUiStore((state) => state.snapshotMode)
  const passportId = id || (snapshotMode ? snapshotPassportId : null)
  const [activeStep, setActiveStep] = useState(0)
  const [passportOverride, setPassportOverride] = useState(null)
  const [selectedSample, setSelectedSample] = useState(() => snapshotMode ? samples[0] : null)
  const [previewUrl, setPreviewUrl] = useState(() => snapshotMode ? '/drawings/pump_shaft.png' : null)
  const [previewType, setPreviewType] = useState('image')
  const [selectedPartner, setSelectedPartner] = useState('fac_oragadam')
  const [shareLevel, setShareLevel] = useState('RFQ')
  const [shareConsentOpen, setShareConsentOpen] = useState(false)
  const [notice, setNotice] = useState(null)
  const [dragging, setDragging] = useState(false)

  const passportQuery = useQuery({
    queryKey: ['passport', passportId],
    queryFn: () => apiRequest(`/passports/${passportId}`),
    enabled: Boolean(passportId),
    staleTime: 30_000,
  })

  const passport = passportOverride || passportQuery.data || null
  const currentStep = activeStep || (passport ? (passport.status === 'CONFIRMED' ? 3 : 1) : 0)

  useEffect(() => () => {
    if (previewUrl?.startsWith('blob:')) URL.revokeObjectURL(previewUrl)
  }, [previewUrl])

  const extract = useMutation({
    mutationFn: async (file) => {
      const body = new FormData()
      body.append('file', file)
      return apiRequest('/passports/extract', { method: 'POST', body })
    },
    onSuccess: (result) => {
      setPassportOverride({
        id: result.passport_id,
        part_id: null,
        status: result.status,
        data: result.data,
        extraction_meta: result.extraction_meta,
        source_sha256: result.extraction_meta.sha256,
        missing_required: result.missing_required,
        needs_review: result.needs_review,
        trace: result.trace,
      })
      setActiveStep(1)
      setNotice(null)
    },
    onError: (error) => setNotice({ tone: 'warning', text: `${error.code || 'EXTRACTION_ERROR'} · ${error.message}` }),
  })

  const manual = useMutation({
    mutationFn: () => apiRequest('/passports/manual', {
      method: 'POST',
      body: JSON.stringify({ fields: { part_name: 'Untitled sample part' } }),
    }),
    onSuccess: (result) => {
      setPassportOverride(result)
      setSelectedSample(null)
      setPreviewUrl(null)
      setActiveStep(1)
      setNotice({ tone: 'info', text: 'Manual draft ready. Cycle times are planner estimates from defaults.' })
    },
    onError: (error) => setNotice({ tone: 'warning', text: `${error.code || 'MANUAL_ERROR'} · ${error.message}` }),
  })

  const patch = useMutation({
    mutationFn: ({ field, value }) => apiRequest(`/passports/${passport.id}`, {
      method: 'PATCH',
      body: JSON.stringify({ data: { [field]: value } }),
    }),
    onSuccess: (result) => setPassportOverride((current) => ({ ...(current || passportQuery.data), ...result })),
    onError: (error) => setNotice({ tone: 'warning', text: `${error.code || 'SAVE_ERROR'} · ${error.message}` }),
  })

  const confirm = useMutation({
    mutationFn: () => apiRequest(`/passports/${passport.id}/confirm`, { method: 'POST' }),
    onSuccess: (result) => {
      setPassportOverride((current) => ({ ...(current || passportQuery.data), ...result }))
      setActiveStep(3)
      setNotice({ tone: 'info', text: `Passport confirmed · part ${result.part_id} created. Cycle times are planner estimates from processes.yaml.` })
    },
    onError: (error) => setNotice({ tone: 'warning', text: `${error.code || 'CONFIRM_ERROR'} · ${error.message}` }),
  })

  const rfq = useQuery({
    queryKey: ['passport-rfq', passport?.id],
    queryFn: () => apiRequest(`/passports/${passport.id}/rfq`),
    enabled: Boolean(passport?.id && passport.status === 'CONFIRMED' && currentStep >= 3),
    staleTime: 30_000,
  })

  const share = useMutation({
    mutationFn: ({ level }) => apiRequest(`/passports/${passport.id}/share`, {
      method: 'POST',
      body: JSON.stringify({ partner_id: selectedPartner, level }),
    }),
    onSuccess: (result) => {
      setShareConsentOpen(false)
      setShareLevel(result.level)
      setNotice({ tone: 'info', text: `${result.level === 'RFQ' ? 'Redacted RFQ' : 'Full passport'} shared with ${selectedPartner}.` })
    },
    onError: (error) => setNotice({ tone: 'warning', text: `${error.code || 'SHARE_ERROR'} · ${error.message}` }),
  })

  const values = useMemo(() => Object.fromEntries(
    Object.entries(passport?.data || {}).map(([key, field]) => [key, field?.value ?? null]),
  ), [passport?.data])
  const fieldState = (key) => passport?.data?.[key] || { value: null, confidence: 'MISSING', source: null }

  const selectSample = async (sample) => {
    if (snapshotMode) return
    setSelectedSample(sample)
    setPreviewType('image')
    const file = await fetch(`/drawings/${sample.filename}`).then((response) => {
      if (!response.ok) throw new Error('Could not load the sample drawing.')
      return response.blob()
    })
    setPreviewUrl(URL.createObjectURL(file))
    extract.mutate(new File([file], sample.filename, { type: 'image/png' }))
  }

  const openFile = (file) => {
    if (!file || snapshotMode) return
    setSelectedSample(null)
    setPreviewUrl(URL.createObjectURL(file))
    setPreviewType(file.type === 'application/pdf' ? 'pdf' : 'image')
    extract.mutate(file)
  }

  const setField = (field, value) => {
    if (snapshotMode) return
    setPassportOverride((current) => {
      const base = current || passportQuery.data
      if (!base) return base
      return {
        ...base,
        data: {
          ...base.data,
          [field]: { ...fieldState(field), value, confidence: 'CONFIRMED', source: 'user' },
        },
      }
    })
  }

  const saveField = (field, value) => {
    if (!snapshotMode && passport?.id && value !== undefined) patch.mutate({ field, value })
  }

  const changeMaterial = (material) => setField('material', material)

  const changeProcessRoute = (raw) => {
    const route = raw.split(/[→,]/).map((process) => process.trim().toUpperCase()).filter(Boolean).map((process) => ({ process }))
    setField('process_route', route)
    saveField('process_route', route)
  }

  const changeDimensions = (index, field, rawValue) => {
    const current = [...(values.dimensions || [])]
    const numeric = ['nominal_mm', 'tol_plus_mm', 'tol_minus_mm'].includes(field)
    current[index] = { ...current[index], [field]: numeric ? (rawValue === '' ? null : Number(rawValue)) : rawValue }
    setField('dimensions', current)
  }

  const canConfirm = Boolean(
    passport && passport.status !== 'CONFIRMED'
    && values.process_route?.length
    && values.material?.grade
    && Number(values.quantity) > 0
    && ((Number(values.tightest_tolerance_mm) >= 0.001) || values.general_tolerance_standard),
  )

  const missingForConfirm = useMemo(() => requiredFields(values), [values])

  const handleDrop = (event) => {
    event.preventDefault()
    setDragging(false)
    openFile(event.dataTransfer.files?.[0])
  }

  const extractMeta = passport?.extraction_meta
  const providerLabel = {
    cache: 'Read from saved result',
    gemini: 'Read by Gemini free tier',
    rules: 'Printed-text rules only',
    manual: 'Entered by hand',
    ollama: 'Local model',
  }[extractMeta?.provider] || 'Not read yet'

  return (
    <main className="passport-page">
      <header className="passport-heading">
        <div><span className="f0-kicker">M2 · PRODUCTION PASSPORT</span><h1>PASSPORTS</h1></div>
        {passport && <Nameplate>{passport.id}</Nameplate>}
      </header>

      <ol className="passport-stepper" aria-label="Passport workflow">
        {steps.map((step, index) => <li key={step} className={currentStep === index ? 'is-current' : currentStep > index ? 'is-done' : ''}><span>{String(index + 1).padStart(2, '0')}</span>{step}</li>)}
      </ol>
      {snapshotMode && <Nameplate>READ-ONLY SAVED PASSPORT</Nameplate>}

      {notice && <Toast tone={notice.tone} onDismiss={() => setNotice(null)}>{notice.text}</Toast>}
      {extract.isError && <Toast tone="warning">{extract.error.message}</Toast>}
      {passportQuery.isError && <Toast tone="warning">{passportQuery.error.message}</Toast>}

      <div className="passport-workbench">
        <section className="passport-drawing">
          <header className="passport-panel-heading"><div><span className="f0-kicker">DRAWING TABLE</span><h2>Source document</h2></div></header>
          {previewUrl ? (
            <div
              className={`passport-preview ${extract.isPending ? 'is-reading' : ''}`}
              onDragOver={(event) => { event.preventDefault(); setDragging(true) }}
              onDragLeave={() => setDragging(false)}
              onDrop={handleDrop}
            >
              {previewType === 'pdf' ? <iframe title="Uploaded drawing PDF" src={previewUrl} /> : <img src={previewUrl} alt={selectedSample?.label || 'Uploaded engineering drawing'} />}
              {extract.isPending && <><div className="passport-scanline" /><div className="passport-reading">Reading your drawing…</div></>}
              <label className="passport-replace-file">Replace drawing
                <input type="file" accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg" onChange={(event) => openFile(event.target.files?.[0])} hidden />
              </label>
            </div>
          ) : (
            <div className={`passport-drop ${dragging ? 'is-dragging' : ''}`} onDragOver={(event) => { event.preventDefault(); setDragging(true) }} onDragLeave={() => setDragging(false)} onDrop={handleDrop}>
              <span className="f0-kicker">{extract.isPending ? 'READING YOUR DRAWING…' : 'DRAWING INPUT'}</span>
              <p>Choose a sample or drop a PDF / PNG / JPG here.</p>
              <label className={`relay-button relay-button--secondary relay-button--small ${snapshotMode ? 'is-disabled' : ''}`}>
                Browse files
                <input type="file" accept=".pdf,.png,.jpg,.jpeg,application/pdf,image/png,image/jpeg" onChange={(event) => openFile(event.target.files?.[0])} disabled={snapshotMode} hidden />
              </label>
            </div>
          )}
          <div className="passport-sample-tray">
            <span className="f0-kicker">SAMPLE DRAWINGS</span>
            <div>
              {samples.map((sample) => (
                <button type="button" disabled={snapshotMode} className={selectedSample?.id === sample.id ? 'is-selected' : ''} key={sample.id} onClick={() => selectSample(sample)}>
                  <img src={`/drawings/${sample.filename}`} alt="" />
                  <span>{sample.label}</span>
                </button>
              ))}
            </div>
          </div>
          <Button variant="ghost" size="small" disabled={snapshotMode || manual.isPending} onClick={() => manual.mutate()}>Create manually</Button>
          {extractMeta && <div className="passport-provider">
            <span className={`passport-provider__dot passport-provider__dot--${extractMeta.provider || 'rules'}`} />
            <span>{providerLabel}</span>{extractMeta.latency_ms != null && <small>{extractMeta.latency_ms} ms</small>}
            {extractMeta.degraded && <Stamp tone="gold">DEGRADED</Stamp>}
          </div>}
        </section>

        <section className="passport-review">
          <header className="passport-panel-heading">
            <div><span className="f0-kicker">PRODUCTION PASSPORT</span><h2>Review fields</h2></div>
            {passport?.status === 'CONFIRMED' && <Stamp tone="gold">CONFIRMED</Stamp>}
          </header>
          {!passport ? (
            <Frame className="passport-empty"><p>Select a sample or drop a drawing to make a draft passport.</p></Frame>
          ) : (
            <>
              {extractMeta?.provider === 'rules' && <Toast tone="warning">Reading service unavailable. Draft built from printed text only. Check every field.</Toast>}
              {(passport.needs_review || []).length > 0 && (
                <div className="passport-review-warning"><span className="f0-kicker">NEEDS REVIEW</span><span>{passport.needs_review.join(', ')}</span></div>
              )}
              <FieldGroup label="Part name" state={fieldState('part_name')} value={values.part_name || ''} onChange={(value) => setField('part_name', value)} onBlur={() => saveField('part_name', values.part_name)} readOnly={snapshotMode} />
              <div className="passport-field-grid">
                {fieldSpecs.filter((field) => field.key !== 'part_name').map((field) => (
                  <PassportFieldEditor
                    key={field.key}
                    spec={field}
                    state={fieldState(field.key)}
                    value={values[field.key]}
                    onChange={(value) => setField(field.key, value)}
                    onBlur={() => saveField(field.key, values[field.key])}
                    readOnly={snapshotMode}
                  />
                ))}
                <label className="passport-field passport-field--route">
                  <span>Process route <ConfidenceBars value={fieldState('process_route').confidence} /></span>
                  <input
                    value={(values.process_route || []).map((item) => typeof item === 'string' ? item : item.process).join(' → ')}
                    placeholder="TURN → MILL"
                    readOnly={snapshotMode}
                    onChange={(event) => setField('process_route', event.target.value.split(/[→,]/).map((process) => ({ process: process.trim().toUpperCase() })).filter((item) => item.process))}
                    onBlur={() => changeProcessRoute((values.process_route || []).map((item) => item.process).join(' → '))}
                  />
                  <small>Planner estimates are editable; the drawing does not contain cycle times.</small>
                </label>
              </div>
              <MaterialEditor state={fieldState('material')} value={values.material} onChange={changeMaterial} onBlur={() => saveField('material', values.material)} readOnly={snapshotMode} />
              <DimensionEditor state={fieldState('dimensions')} rows={values.dimensions || []} onChange={changeDimensions} onBlur={() => saveField('dimensions', values.dimensions)} readOnly={snapshotMode} />
              {(fieldState('tightest_tolerance_mm').candidates || []).length > 1 && (
                <div className="passport-candidates">
                  <span className="f0-kicker">CANDIDATES · RULES VALUE IS DEFAULT</span>
                    {fieldState('tightest_tolerance_mm').candidates.map((candidate, index) => (
                      <button key={`${candidate}-${index}`} type="button" disabled={snapshotMode} onClick={() => { setField('tightest_tolerance_mm', candidate); saveField('tightest_tolerance_mm', candidate) }}>
                      {candidate} mm · {index === 0 ? 'printed-text rules' : 'vision reading'}
                    </button>
                  ))}
                </div>
              )}
              {missingForConfirm.length > 0 && (
                <div className="passport-missing" role="status">
                  <span className="f0-kicker">CONFIRM DISABLED · FIELDS MISSING</span>
                  <span>{missingForConfirm.join(' · ')}</span>
                </div>
              )}
              <div className="passport-confirm-row">
                <Button disabled={snapshotMode || !canConfirm || confirm.isPending} loading={confirm.isPending} onClick={() => confirm.mutate()}>Confirm passport</Button>
                <small>Cycle times are planner estimates from defaults. A drawing does not contain them.</small>
              </div>
            </>
          )}
        </section>
      </div>

      {passport?.status === 'CONFIRMED' && currentStep >= 3 && (
        <section className="passport-rfq-section">
          <header className="passport-panel-heading">
            <div><span className="f0-kicker">STEP 4 · REDACTED RFQ</span><h2>Share technical requirements</h2></div>
            {rfq.isLoading ? <span className="f0-kicker">BUILDING REDACTED RFQ…</span> : rfq.data && <Nameplate>{rfq.data.rfq_ref}</Nameplate>}
          </header>
          {rfq.isError && <Toast tone="warning">{rfq.error.message}</Toast>}
          {rfq.data && (
            <div className="passport-rfq-columns">
              <PaperSheet title="Original drawing · owner view">
                {previewUrl && <img className="passport-rfq-preview" src={previewUrl} alt="Original drawing preview" />}
                <p>{values.part_name || 'Part name not entered'}</p>
                <p>{values.customer || 'Customer not entered'} · {values.drawing_no || 'Drawing number not entered'} · Rev {values.revision || '—'}</p>
              </PaperSheet>
              <PaperSheet title={`Redacted RFQ · ${rfq.data.rfq_ref}`}>
                <div className="passport-rfq-redacted">
                  <span className="f0-kicker">CUSTOMER IDENTIFIERS REMOVED</span>
                  {['CUSTOMER', 'DRAWING NUMBER', 'PART NAME / PART NUMBER', 'REVISION', 'TITLE BLOCK'].map((label) => <i key={label} aria-label={`${label} redacted`} />)}
                </div>
                <dl className="passport-rfq-fields">
                  {Object.entries(rfq.data.content).map(([key, value]) => (
                    <div key={key}><dt>{key.replaceAll('_', ' ')}</dt><dd>{formatRfqValue(value)}</dd></div>
                  ))}
                </dl>
                <pre className="passport-rfq-text">{printableRfqText(rfq.data)}</pre>
                <div className="passport-redaction-report">
                  Removed: {rfq.data.redaction_report.removed_keys.join(', ') || 'none'}.
                </div>
              </PaperSheet>
            </div>
          )}
          <div className="passport-share">
            <div><span className="f0-kicker">STEP 5 · EXPLICIT CONSENT</span><p>Share redacted RFQ by default. Full passport sharing requires customer permission.</p></div>
            <label className="passport-share__partner">Partner
                <select value={selectedPartner} disabled={snapshotMode} onChange={(event) => setSelectedPartner(event.target.value)}>
                <option value="fac_oragadam">Sample Components (Oragadam)</option>
                <option value="fac_hosur">Sample Engineering (Hosur)</option>
                <option value="fac_peenya">Sample Works (Peenya)</option>
                <option value="fac_cbe">Sample Tools (Coimbatore)</option>
              </select>
            </label>
            <Segmented label="Share level" disabled={snapshotMode} value={shareLevel} onChange={(level) => { setShareLevel(level); setActiveStep(4) }} options={[
              { value: 'RFQ', label: 'Redacted RFQ' },
              { value: 'FULL', label: 'Full passport' },
            ]} />
            <Button variant="secondary" disabled={snapshotMode || share.isPending || !rfq.data} onClick={() => shareLevel === 'FULL' ? setShareConsentOpen(true) : share.mutate({ level: 'RFQ' })}>
              {shareLevel === 'FULL' ? 'Review full-share consent' : 'Share redacted RFQ'}
            </Button>
          </div>
          {share.isError && <Toast tone="warning">{share.error.message}</Toast>}
          {share.isSuccess && <Toast tone="info">{share.data.level} share recorded for {share.data.partner_id}.</Toast>}
        </section>
      )}

      {shareConsentOpen && (
        <div className="passport-consent-overlay">
          <section className="passport-consent" role="dialog" aria-modal="true" aria-label="Full passport sharing consent">
            <span className="f0-kicker">FULL-PASSPORT SHARE</span>
            <h2>Share full drawing details?</h2>
            <p>The partner will see the full drawing details. Only do this with the customer's permission.</p>
            <div><Button variant="ghost" onClick={() => setShareConsentOpen(false)}>Cancel</Button><Button disabled={snapshotMode} onClick={() => share.mutate({ level: 'FULL' })}>I have permission · Share full</Button></div>
          </section>
        </div>
      )}
    </main>
  )
}

function FieldGroup({ label, state, value, onChange, onBlur, readOnly = false }) {
  return (
    <label className="passport-field passport-field--wide">
      <span>{label}<ConfidenceBars value={state.confidence} /><small>{state.source || 'not found'}</small></span>
      <input value={value} readOnly={readOnly} onChange={(event) => onChange(event.target.value)} onBlur={onBlur} />
    </label>
  )
}

function PassportFieldEditor({ spec, state, value, onChange, onBlur, readOnly = false }) {
  const normalized = value == null ? '' : value
  return (
    <label className="passport-field">
      <span>{spec.label}<ConfidenceBars value={state.confidence} /><small>{state.source || 'not found'}</small></span>
      <input
        type={spec.type}
        step={spec.type === 'number' ? 'any' : undefined}
        value={normalized}
        readOnly={readOnly}
        onChange={(event) => onChange(spec.type === 'number' ? event.target.value === '' ? null : Number(event.target.value) : event.target.value)}
        onBlur={onBlur}
      />
    </label>
  )
}

function MaterialEditor({ state, value, onChange, onBlur, readOnly = false }) {
  const material = value || {}
  return (
    <div className="passport-field passport-field--material">
      <span>Material <ConfidenceBars value={state.confidence} /><small>{state.source || 'not found'}</small></span>
      <div>
        <Field label="Grade" value={material.grade || ''} disabled={readOnly} onChange={(event) => onChange({ ...material, grade: event.target.value })} onBlur={onBlur} />
        <Field label="Standard" value={material.standard || ''} disabled={readOnly} onChange={(event) => onChange({ ...material, standard: event.target.value || null })} onBlur={onBlur} />
        <Field label="Form" value={material.form || ''} disabled={readOnly} onChange={(event) => onChange({ ...material, form: event.target.value || null })} onBlur={onBlur} />
      </div>
    </div>
  )
}

function DimensionEditor({ state, rows, onChange, onBlur, readOnly = false }) {
  return (
    <section className="passport-dimensions">
      <header><span className="f0-kicker">DIMENSIONS · MILLIMETRES</span><ConfidenceBars value={state.confidence} /></header>
      {!rows.length ? <p>No dimensions found. Add them after a drawing is read.</p> : (
        <div className="passport-dimensions__table">
          <div className="passport-dimensions__row is-header"><span>Feature</span><span>Nominal</span><span>+ tol</span><span>− tol</span><span>Critical</span></div>
          {rows.map((row, index) => (
            <div className="passport-dimensions__row" key={`${row.label}-${index}`}>
              <input aria-label={`${row.label} label`} value={row.label || ''} disabled={readOnly} onChange={(event) => onChange(index, 'label', event.target.value)} onBlur={onBlur} />
              {['nominal_mm', 'tol_plus_mm', 'tol_minus_mm'].map((field) => (
                <input key={field} type="number" step="any" aria-label={`${row.label} ${field}`} value={row[field] ?? ''} disabled={readOnly} onChange={(event) => onChange(index, field, event.target.value)} onBlur={onBlur} />
              ))}
              <input type="checkbox" aria-label={`${row.label} critical`} checked={Boolean(row.critical)} disabled={readOnly} onChange={(event) => onChange(index, 'critical', event.target.checked)} onBlur={onBlur} />
            </div>
          ))}
        </div>
      )}
    </section>
  )
}

function requiredFields(values) {
  const missing = []
  if (!Array.isArray(values.process_route) || !values.process_route.length) missing.push('process route')
  if (!values.material?.grade) missing.push('material grade')
  if (!(Number(values.quantity) > 0)) missing.push('quantity')
  if (!(Number(values.tightest_tolerance_mm) >= 0.001) && !values.general_tolerance_standard) missing.push('tolerance or general standard')
  return missing
}

function formatRfqValue(value) {
  if (Array.isArray(value)) return value.map((item) => typeof item === 'object' ? item.process || JSON.stringify(item) : item).join(' → ')
  if (value && typeof value === 'object') return Object.entries(value).map(([key, item]) => `${key}: ${item}`).join(' · ')
  return String(value)
}

function printableRfqText(rfq) {
  // The current API generates a second random RFQ ref inside its text template.
  // Keep this screen internally consistent with the structured RfqOut.rfq_ref.
  return String(rfq.text || '').replace(/RFQ-[A-F0-9]{8}/gi, rfq.rfq_ref)
}
