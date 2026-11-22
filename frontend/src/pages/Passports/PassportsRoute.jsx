import { lazy, Suspense } from 'react'
import { Navigate, useParams } from 'react-router-dom'
import { useUiStore } from '../../store/ui'
import { snapshotPassportId } from '../../api/snapshot'

const Passports = lazy(() => import('./Passports'))

export default function PassportsRoute() {
  const { id } = useParams()
  const snapshotMode = useUiStore((state) => state.snapshotMode)
  if (snapshotMode && !id) return <Navigate to={`/app/passports/${snapshotPassportId}`} replace />
  return <Suspense fallback={<div className="f0-content">Loading passport workspace…</div>}><Passports key={id || 'new'} /></Suspense>
}
