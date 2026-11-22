import { lazy, Suspense } from 'react'

const WhatIf = lazy(() => import('./WhatIf'))

export default function WhatIfRoute() {
  return <Suspense fallback={<div className="f0-content">Loading what-if workspace…</div>}><WhatIf /></Suspense>
}
