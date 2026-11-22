import { lazy, Suspense } from 'react'

const Partners = lazy(() => import('./Partners'))

export default function PartnersRoute() {
  return <Suspense fallback={<div className="f0-content">Loading backup network…</div>}><Partners /></Suspense>
}
