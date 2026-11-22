import { lazy, Suspense } from 'react'
import { Navigate, useParams } from 'react-router-dom'
import { useUiStore } from '../../store/ui'
import { snapshotRecoveryRequestId } from '../../api/snapshot'

const Recovery = lazy(() => import('./Recovery'))

export default function RecoveryRoute() {
  const { id } = useParams()
  const snapshotMode = useUiStore((state) => state.snapshotMode)
  if (snapshotMode && !id) return <Navigate to={`/app/recovery/${snapshotRecoveryRequestId}`} replace />
  return <Suspense fallback={<div className="f0-content">Loading recovery request…</div>}><Recovery /></Suspense>
}
