import { lazy, Suspense } from 'react'

const WeakPoints = lazy(() => import('./WeakPoints'))

export default function WeakPointsRoute() {
  return <Suspense fallback={<div className="f0-content">Loading dependency drawing…</div>}><WeakPoints /></Suspense>
}
