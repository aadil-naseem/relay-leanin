import snapshot from '../data/snapshot.json' with { type: 'json' }

export const snapshotCapturedAt = snapshot.captured_at_utc
export const snapshotAvailable = snapshot.schema_version === 1
export const snapshotRecoveryRequestId = snapshot.recovery_request.id
export const snapshotPassportId = snapshot.passport.id

const clone = (value) => JSON.parse(JSON.stringify(value))

export function isSnapshotRequestAllowed(path, method = 'GET') {
  const normalizedMethod = method.toUpperCase()
  const pathname = new URL(path, 'http://snapshot.local').pathname
  return normalizedMethod === 'GET'
    || (normalizedMethod === 'POST' && pathname === '/matching/search')
}

export function resolveSnapshotRequest(path, method = 'GET') {
  const normalizedMethod = method.toUpperCase()
  const pathname = new URL(path, 'http://snapshot.local').pathname

  if (normalizedMethod === 'POST' && pathname === '/matching/search') {
    return clone(snapshot.matching)
  }
  if (normalizedMethod !== 'GET') return null

  const staticRoutes = new Map([
    ['/health', 'health'],
    ['/demo/state', 'demo_state'],
    ['/dashboard/fac_owner', 'dashboard'],
    ['/factories/fac_owner/spof', 'spof'],
    ['/exposure/map', 'exposure_map'],
    ['/factories/fac_owner/exposure', 'owner_exposure'],
    ['/readiness/fac_owner', 'readiness'],
    ['/readiness/fac_owner/actions', 'readiness_actions'],
    ['/readiness/fac_owner/history', 'readiness_history'],
    ['/factories', 'factories'],
    ['/factories/fac_owner/relationships', 'relationships'],
    ['/factories/fac_owner/orders', 'orders'],
    ['/factories/fac_owner/parts', 'parts'],
  ])
  const staticKey = staticRoutes.get(pathname)
  if (staticKey) {
    const response = clone(snapshot[staticKey])
    if (staticKey === 'health') {
      response.status = 'snapshot'
      response.db = 'offline'
    }
    return response
  }

  const recoveryBase = `/recovery-requests/${snapshot.recovery_request.id}`
  if (pathname === recoveryBase) return clone(snapshot.recovery_request)
  if (pathname === `${recoveryBase}/tracking`) return clone(snapshot.recovery_tracking)
  if (pathname === `${recoveryBase}/handover`) return clone(snapshot.recovery_handover)

  const passportBase = `/passports/${snapshot.passport.id}`
  if (pathname === passportBase) return clone(snapshot.passport)
  if (pathname === `${passportBase}/rfq`) return clone(snapshot.rfq)

  if (pathname === `/stress-tests/${snapshot.stress_test.id}`) return clone(snapshot.stress_test)
  return null
}
