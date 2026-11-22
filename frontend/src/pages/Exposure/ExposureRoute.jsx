import { lazy, Suspense } from 'react'

const Exposure = lazy(() => import('./Exposure'))

export default function ExposureRoute() {
  return <Suspense fallback={<div className="f0-content">Loading exposure screen…</div>}><Exposure /></Suspense>
}
