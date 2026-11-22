import test from 'node:test'
import assert from 'node:assert/strict'
import { formatMoney, formatOdometerValue } from '../src/lib/format.js'
import {
  backupStatusLabel,
  exclusionReasonLabel,
  hazardName,
  readinessReasonLabel,
  recoveryStatusLabel,
  routeStepLabel,
  statusStyle,
} from '../src/lib/status.js'

test('Money formatting uses lakhs and crores', () => {
  assert.equal(formatMoney(2_150_000), '₹21.5 L')
  assert.equal(formatMoney(10_000_000), '₹1 Cr')
  assert.equal(formatMoney(125_000_000), '₹12.5 Cr')
})

test('Odometer formatter ends at the exact formatted value', () => {
  assert.equal(formatOdometerValue(53.9, 1), '53.9')
  assert.equal(formatOdometerValue(2150000), '21,50,000')
})

test('each risk level has distinct text, tone, and shape encoding', () => {
  const values = ['LOW', 'MODERATE', 'HIGH', 'SEVERE']
  const items = values.map((value) => statusStyle('risk', value))
  assert.deepEqual(items.map((item) => item.label), ['Low', 'Moderate', 'High', 'Severe'])
  assert.equal(new Set(items.map((item) => item.shape)).size, values.length)
  assert.deepEqual(items.map((item) => item.tone), ['sky', 'pale', 'sun', 'sun'])
  assert.equal(items[3].shape, 'chevron')
})

test('every order and fallback value is explicitly mapped', () => {
  for (const value of ['ON_TRACK', 'AT_RISK', 'LATE']) {
    const item = statusStyle('order', value)
    assert.ok(item.label)
    assert.ok(item.glyph)
    assert.ok(item.shape)
  }
  for (const value of ['READY', 'POTENTIAL_ONLY', 'NONE']) {
    const item = statusStyle('fallback', value)
    assert.ok(item.label)
    assert.ok(item.glyph)
    assert.ok(item.shape)
  }
})

test('all backup statuses including STALE have distinct textual/shape treatment', () => {
  const values = ['READY', 'STALE', 'APPROVAL_PENDING', 'ASSESSMENT_IN_PROGRESS', 'POTENTIAL_MATCH', 'UNAVAILABLE_EXPIRED']
  const items = values.map((value) => statusStyle('backup', value))
  assert.equal(new Set(items.map((item) => item.label)).size, values.length)
  assert.equal(new Set(items.map((item) => item.shape)).size, values.length)
  const excluded = statusStyle('backup', 'READY', 'SAME_HAZARD_ZONE')
  assert.equal(excluded.label, 'Excluded · in the same flood zone as you')
  assert.ok(!excluded.label.includes('_'), 'exclusion reasons must read as plain language')
})

test('API reason codes are explained in plain language', () => {
  assert.equal(exclusionReasonLabel('ALSO_EXPOSED_SAME_EVENT'), 'in the same storm footprint as you')
  assert.equal(readinessReasonLabel('NO_PARTNER_ELIGIBLE'), 'no capable partner')
  assert.equal(backupStatusLabel('APPROVAL_PENDING'), 'Approval pending')
  assert.equal(routeStepLabel('TECHNICAL_AND_CUSTOMER_APPROVALS'), 'Technical and customer approvals')
  assert.equal(hazardName('ACCESS_BLOCKED'), 'Access blocked')
  assert.equal(recoveryStatusLabel('ACTIVE'), 'Partner engaged')
  // Unknown codes still degrade to readable text rather than raw snake_case.
  assert.equal(exclusionReasonLabel('SOME_NEW_REASON'), 'Some new reason')
})

test('confidence levels carry distinct signal-bar counts', () => {
  const values = ['HIGH', 'MEDIUM', 'LOW', 'MISSING', 'CONFIRMED']
  assert.deepEqual(values.map((value) => statusStyle('confidence', value).bars), [3, 2, 1, 0, 3])
  assert.equal(new Set(values.map((value) => statusStyle('confidence', value).label)).size, values.length)
})
