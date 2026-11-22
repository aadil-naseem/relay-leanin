import test from 'node:test'
import assert from 'node:assert/strict'
import snapshot from '../src/data/snapshot.json' with { type: 'json' }
import {
  isSnapshotRequestAllowed,
  resolveSnapshotRequest,
  snapshotAvailable,
} from '../src/api/snapshot.js'

test('replay snapshot contains the required named offline demo data', () => {
  assert.equal(snapshotAvailable, true)
  assert.equal(snapshot.schema_version, 1)
  assert.equal(snapshot.demo_state.weather_mode, 'replay')
  assert.equal(snapshot.data_label, 'SIMULATED SAMPLE')
  for (const key of [
    'dashboard',
    'spof',
    'exposure_map',
    'relationships',
    'readiness',
    'stress_test',
    'recovery_request',
    'passport',
  ]) {
    assert.ok(snapshot[key], `snapshot is missing ${key}`)
  }
  assert.equal(snapshot.passport.status, 'CONFIRMED')
  assert.equal(snapshot.recovery_request.selected_partner_id, 'fac_oragadam')
  assert.ok(snapshot.recovery_tracking.steps.every((step) => step.state === 'DONE'))
})

test('snapshot routing serves the desk and every captured screen read-only', () => {
  assert.equal(resolveSnapshotRequest('/dashboard/fac_owner').factory.id, 'fac_owner')
  assert.equal(resolveSnapshotRequest('/health').status, 'snapshot')
  assert.equal(resolveSnapshotRequest('/health').db, 'offline')
  assert.ok(resolveSnapshotRequest('/factories/fac_owner/spof').items.length > 0)
  assert.ok(resolveSnapshotRequest('/exposure/map').points.length > 0)
  assert.ok(resolveSnapshotRequest('/factories/fac_owner/relationships').length > 0)
  assert.equal(
    resolveSnapshotRequest(`/stress-tests/${snapshot.stress_test.id}`).id,
    snapshot.stress_test.id,
  )
  assert.equal(
    resolveSnapshotRequest(`/recovery-requests/${snapshot.recovery_request.id}/tracking`).steps.length,
    snapshot.recovery_tracking.steps.length,
  )
  assert.equal(
    resolveSnapshotRequest(`/passports/${snapshot.passport.id}/rfq`).rfq_ref,
    snapshot.rfq.rfq_ref,
  )
})

test('snapshot blocks mutations but permits the read-only matching search', () => {
  assert.equal(isSnapshotRequestAllowed('/matching/search', 'POST'), true)
  assert.equal(isSnapshotRequestAllowed('/demo/reset', 'POST'), false)
  assert.equal(isSnapshotRequestAllowed('/relationships/rel_1/status', 'PATCH'), false)
  assert.equal(isSnapshotRequestAllowed('/passports/pas_1', 'PUT'), false)
  assert.equal(isSnapshotRequestAllowed('/dashboard/fac_owner', 'GET'), true)
  assert.ok(resolveSnapshotRequest('/matching/search', 'POST').candidates.length > 0)
  assert.equal(resolveSnapshotRequest('/demo/reset', 'POST'), null)
})

test('snapshot response clones cannot mutate the committed pack', () => {
  const response = resolveSnapshotRequest('/dashboard/fac_owner')
  response.factory.name = 'Changed in test'
  assert.notEqual(response.factory.name, snapshot.dashboard.factory.name)
})
