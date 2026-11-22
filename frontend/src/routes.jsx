import { lazy, Suspense } from 'react'
import { createBrowserRouter } from 'react-router-dom'
import { AppShell } from './app/AppShell'
import { PlaceholderRoute } from './app/PlaceholderRoute'
import Desk from './pages/Desk/Desk'
import ExposureRoute from './pages/Exposure/ExposureRoute'
import WeakPointsRoute from './pages/WeakPoints/WeakPointsRoute'
import WhatIfRoute from './pages/WhatIf/WhatIfRoute'
import RecoveryRoute from './pages/Recovery/RecoveryRoute'
import PartnersRoute from './pages/Partners/PartnersRoute'
import PassportsRoute from './pages/Passports/PassportsRoute'
import Proof from './pages/Proof/Proof'
import { SystemNotFound } from './pages/System/SystemScreens'
import Landing from './pages/Landing/Landing'

// Route configuration is intentionally a non-component export in this module.
// oxlint-disable-next-line react/only-export-components
const ComponentKit = lazy(() => import('./pages/Kit/ComponentKit'))

const appScreens = [
  { path: '', number: 'S1', title: 'Desk', route: '/app' },
  { path: 'recovery', number: 'S6', title: 'Recovery', route: '/app/recovery' },
  { path: 'proof', number: 'S8', title: 'Proof & Method', route: '/app/proof' },
]

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Landing />,
  },
  {
    path: '/app',
    element: <AppShell />,
    children: [
      ...appScreens.map((screen) => ({
        ...(screen.path ? { path: screen.path } : { index: true }),
        element: screen.path === ''
          ? <Desk />
          : screen.path === 'recovery'
            ? <RecoveryRoute />
            : screen.path === 'proof'
              ? <Proof />
              : <PlaceholderRoute number={screen.number} title={screen.title} route={screen.route} />,
      })),
      { path: 'weak-points', element: <WeakPointsRoute /> },
      { path: 'exposure', element: <ExposureRoute /> },
      { path: 'what-if', element: <WhatIfRoute /> },
      { path: 'what-if/:id', element: <WhatIfRoute /> },
      { path: 'recovery/:id', element: <RecoveryRoute /> },
      { path: 'partners', element: <PartnersRoute /> },
      { path: 'passports', element: <PassportsRoute /> },
      { path: 'passports/:id', element: <PassportsRoute /> },
      { path: '_kit', element: <Suspense fallback={<div className="f0-content">Loading component kit…</div>}><ComponentKit /></Suspense> },
      { path: '*', element: <SystemNotFound /> },
    ],
  },
  {
    path: '*',
    element: <SystemNotFound />,
  },
])
