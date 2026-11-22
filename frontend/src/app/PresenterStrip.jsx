import { useEffect, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { apiRequest } from '../api/client'
import { useUiStore } from '../store/ui'
import { Button } from '../components/primitives'

const scriptSteps = [
  { label: 'Landing', route: '/' },
  { label: 'Desk', route: '/app' },
  { label: 'What-if', route: '/app/what-if' },
  { label: 'Weak points', route: '/app/weak-points' },
  { label: 'Passports', route: '/app/passports' },
  { label: 'Recovery · request', route: '/app/recovery' },
  { label: 'Recovery · handover', route: '/app/recovery' },
  { label: 'Partners', route: '/app/partners' },
]

export function PresenterStrip({ onNavigate }) {
  const enabled = useUiStore((state) => state.presenterMode)
  const hidden = useUiStore((state) => state.presenterHidden)
  const step = useUiStore((state) => state.presenterStep)
  const recoveryId = useUiStore((state) => state.presenterRecoveryId)
  const setPreference = useUiStore((state) => state.setPreference)
  const setStep = useUiStore((state) => state.goToPresenterStep)
  const [elapsed, setElapsed] = useState(0)
  const dashboard = useQuery({
    queryKey: ['dashboard', 'fac_owner'],
    queryFn: () => apiRequest('/dashboard/fac_owner'),
    enabled,
    staleTime: 30_000,
  })

  useEffect(() => {
    if (!enabled) return undefined
    const started = Date.now()
    const timer = window.setInterval(() => setElapsed(Math.floor((Date.now() - started) / 1000)), 1000)
    return () => window.clearInterval(timer)
  }, [enabled])

  if (!enabled || hidden) return null
  const minutes = Math.floor(elapsed / 60)
  const seconds = String(elapsed % 60).padStart(2, '0')

  return (
    <aside className="relay-presenter" aria-label="Presenter mode">
      <span className="relay-presenter__timer">{minutes}:{seconds}</span>
      <div className="relay-presenter__steps">
        {scriptSteps.map((item, index) => (
          <button type="button" key={item.label} className={step === index ? 'is-active' : ''} onClick={() => { setStep(index); onNavigate(resolveRoute(index, dashboard.data, recoveryId)) }}>
            <span>{String(index).padStart(2, '0')}</span>{item.label}
          </button>
        ))}
      </div>
      <Button variant="ghost" size="small" onClick={() => setPreference('presenterHidden', true)} aria-label="Hide presenter strip">H</Button>
    </aside>
  )
}

function resolveRoute(step, dashboard, recoveryId) {
  if (step === 2 && dashboard?.alert?.stress_test_id) return `/app/what-if/${dashboard.alert.stress_test_id}`
  if ((step === 5 || step === 6) && recoveryId) return `/app/recovery/${recoveryId}`
  return scriptSteps[step]?.route || '/app'
}
