import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { apiRequest } from '../api/client'
import { queryClient } from '../api/queryClient'
import { useHealth } from '../api/hooks/useHealth'
import { DataLabelBadge, ShiftClock, StackLight, WeatherSourceBadge } from '../components/domain'
import { Button, Kbd } from '../components/primitives'
import { RelayNavigationContext } from './navigation'
import { StageControls } from './StageControls'
import { PresenterStrip } from './PresenterStrip'
import { useUiStore } from '../store/ui'
import { BackendUnavailable } from '../pages/System/SystemScreens'
import { snapshotAvailable, snapshotCapturedAt } from '../api/snapshot'

const navItems = [
  { path: '/app', label: 'Desk', glyph: '▦' },
  { path: '/app/weak-points', label: 'Weak points', glyph: '⊗' },
  { path: '/app/exposure', label: 'Exposure', glyph: '≋' },
  { path: '/app/passports', label: 'Passports', glyph: '▤' },
  { path: '/app/what-if', label: 'What-if', glyph: 'ϟ' },
  { path: '/app/recovery', label: 'Recovery', glyph: '⏚' },
  { path: '/app/partners', label: 'Partners', glyph: '◉' },
  { path: '/app/proof', label: 'Proof', glyph: '⌕' },
]

function useIstClock() {
  const [time, setTime] = useState('--:--')
  useEffect(() => {
    const update = () => setTime(new Intl.DateTimeFormat('en-GB', {
      timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit', hour12: false,
    }).format(new Date()))
    const timer = window.setInterval(update, 1000)
    update()
    return () => window.clearInterval(timer)
  }, [])
  return time
}

function isEditable(target) {
  return target instanceof HTMLElement
    && (target.isContentEditable || ['INPUT', 'TEXTAREA', 'SELECT'].includes(target.tagName))
}

export function AppShell() {
  const navigate = useNavigate()
  const location = useLocation()
  const snapshotMode = useUiStore((state) => state.snapshotMode)
  const setUiPreference = useUiStore((state) => state.setPreference)
  const health = useHealth({ enabled: !snapshotMode })
  const demo = useQuery({
    queryKey: ['demo-state'],
    queryFn: () => apiRequest('/demo/state'),
    staleTime: 30_000,
    enabled: !health.isError,
  })
  const presenterMode = useUiStore((state) => state.presenterMode)
  const presenterStep = useUiStore((state) => state.presenterStep)
  const presenterRecoveryId = useUiStore((state) => state.presenterRecoveryId)
  const setPresenterStep = useUiStore((state) => state.goToPresenterStep)
  const presenterDashboard = useQuery({
    queryKey: ['dashboard', 'fac_owner'],
    queryFn: () => apiRequest('/dashboard/fac_owner'),
    enabled: presenterMode && !health.isError,
    staleTime: 30_000,
  })
  const [railPinned, setRailPinned] = useState(false)
  const [paletteOpen, setPaletteOpen] = useState(false)
  const [paletteQuery, setPaletteQuery] = useState('')
  const [stageOpen, setStageOpen] = useState(false)
  const [shutter, setShutter] = useState(false)
  const time = useIstClock()
  const timers = useRef([])

  useEffect(() => () => timers.current.forEach(window.clearTimeout), [])

  const go = useCallback((path) => {
    if (path === location.pathname) return
    if (useUiStore.getState().reduceMotion || window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      setShutter(false)
      navigate(path)
      return
    }
    setShutter(true)
    timers.current.push(window.setTimeout(() => {
      navigate(path)
      timers.current.push(window.setTimeout(() => setShutter(false), 320))
    }, 240))
  }, [location.pathname, navigate])

  const resetDemo = useCallback(async () => {
    if (snapshotMode) return
    await apiRequest('/demo/reset', { method: 'POST' })
    try {
      sessionStorage.removeItem('relay-desk-opened')
      sessionStorage.removeItem('relay-presenter-started')
    } catch {
      // Storage is optional; demo reset still succeeds.
    }
    setUiPreference('presenterRecoveryId', null)
    setPresenterStep(1)
    go('/app')
    await queryClient.invalidateQueries()
  }, [go, setPresenterStep, setUiPreference, snapshotMode])

  const presenterRoute = useCallback((step) => {
    if (step === 0) return '/'
    if (step === 2 && presenterDashboard.data?.alert?.stress_test_id) return `/app/what-if/${presenterDashboard.data.alert.stress_test_id}`
    if ((step === 5 || step === 6) && presenterRecoveryId) return `/app/recovery/${presenterRecoveryId}`
    return ['/app', '/app', '/app/what-if', '/app/weak-points', '/app/passports', '/app/recovery', '/app/recovery', '/app/partners'][step] || '/app'
  }, [presenterDashboard.data, presenterRecoveryId])

  useEffect(() => {
    const onKeyDown = (event) => {
      if (isEditable(event.target)) return
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        setPaletteOpen((open) => !open)
        return
      }
      if (event.key === '/' && !event.ctrlKey && !event.metaKey) {
        event.preventDefault()
        setPaletteOpen(true)
        return
      }
      if (event.key === 'Escape') {
        setPaletteOpen(false)
        setStageOpen(false)
        return
      }
      if (presenterMode && event.key === 'ArrowRight') {
        event.preventDefault()
        const next = Math.min(7, presenterStep + 1)
        setPresenterStep(next)
        go(presenterRoute(next))
        return
      }
      if (presenterMode && event.key === 'ArrowLeft') {
        event.preventDefault()
        const next = Math.max(0, presenterStep - 1)
        setPresenterStep(next)
        go(presenterRoute(next))
        return
      }
      if (presenterMode && event.key.toLowerCase() === 'r') {
        event.preventDefault()
        resetDemo()
        return
      }
      if (presenterMode && event.key.toLowerCase() === 'h') {
        event.preventDefault()
        setUiPreference('presenterHidden', !useUiStore.getState().presenterHidden)
        return
      }
      const number = Number(event.key)
      if (number >= 1 && number <= 8) go(navItems[number - 1].path)
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [go, presenterMode, presenterRoute, presenterStep, resetDemo, setPresenterStep, setUiPreference])

  const commands = useMemo(() => [
    ...navItems.map((item) => ({ label: `Go to ${item.label}`, detail: item.path, path: item.path })),
    { label: 'Open Stage Controls', detail: 'Drawer', action: () => setStageOpen(true) },
    { label: 'Reset demo', detail: 'Open Stage Controls · confirmation required', action: () => setStageOpen(true) },
  ], [])
  const filteredCommands = commands.filter((command) =>
    `${command.label} ${command.detail}`.toLowerCase().includes(paletteQuery.toLowerCase()))

  const runCommand = (command) => {
    setPaletteOpen(false)
    setPaletteQuery('')
    if (command.path) go(command.path)
    else command.action?.()
  }

  const current = navItems.find((item) => item.path === location.pathname)
    || navItems.find((item) => location.pathname.startsWith(`${item.path}/`))
  const healthState = snapshotMode ? 'snapshot' : health.data?.status === 'ok' ? 'ok' : health.isError ? 'error' : 'checking'

  if (health.isError && !snapshotMode) {
    const retryBackend = async () => {
      const result = await health.refetch()
      if (result.data?.status === 'ok') await queryClient.invalidateQueries()
    }
    const openSnapshot = () => {
      queryClient.clear()
      setUiPreference('snapshotMode', true)
      navigate('/app', { replace: true })
    }
    return (
      <BackendUnavailable
        error={health.error}
        retrying={health.isFetching}
        onRetry={retryBackend}
        onOpenSnapshot={snapshotAvailable ? openSnapshot : undefined}
        snapshotCapturedAt={snapshotCapturedAt}
      />
    )
  }

  const leaveSnapshot = () => {
    queryClient.clear()
    setUiPreference('snapshotMode', false)
  }

  return (
    <RelayNavigationContext.Provider value={go}>
    <div className={`relay-app ${railPinned ? 'rail-pinned' : ''}`} data-snapshot-mode={snapshotMode || undefined}>
      <header className="relay-status-strip">
        <button className="relay-wordmark" type="button" onClick={() => go('/')}>RELAY</button>
        <span className="relay-factory-name">Sample Precision Components · Ambattur</span>
        <div className="relay-status-strip__right">
          <ShiftClock time={time} />
          <DataLabelBadge />
          <WeatherSourceBadge
            source={health.data?.weather_mode === 'live' ? 'live' : demo.data?.weather_mode || health.data?.weather_mode || 'replay'}
            degraded={Boolean(demo.isError || health.isError)}
          />
          <span className="relay-health" data-state={healthState} role="status">
            <i aria-hidden="true" />{snapshotMode ? 'SNAPSHOT' : healthState === 'ok' ? 'API' : healthState === 'error' ? 'OFFLINE' : 'CHECK'}
          </span>
          <StackLight exposure="SEVERE" readiness={54} freshness={demo.data?.weather_mode || 'replay'} />
          <Button variant="ghost" size="small" onClick={() => setStageOpen(true)}>Stage <Kbd>`</Kbd></Button>
          <Button variant="ghost" size="small" aria-label="Open command palette ⌘K" onClick={() => setPaletteOpen(true)}><Kbd>⌘K</Kbd></Button>
        </div>
      </header>

      <aside
        className="relay-rail"
        data-pinned={railPinned}
        onMouseEnter={() => !railPinned && document.body.classList.add('relay-rail-hover')}
        onMouseLeave={() => document.body.classList.remove('relay-rail-hover')}
      >
        <button className="relay-rail__pin" type="button" onClick={() => setRailPinned((value) => !value)} aria-label={railPinned ? 'Collapse navigation' : 'Pin navigation'}>
          <span aria-hidden="true">R</span><span className="relay-rail__label">RELAY</span>
        </button>
        <nav aria-label="Main navigation">
          {navItems.map((item, index) => (
            <button
              key={item.path}
              type="button"
              className={`relay-rail__item ${current?.path === item.path ? 'is-active' : ''}`}
              aria-current={current?.path === item.path ? 'page' : undefined}
              onClick={() => go(item.path)}
              title={item.label}
            >
              <span className="relay-rail__glyph" aria-hidden="true">{item.glyph}</span>
              <span className="relay-rail__label">{item.label}</span>
              <Kbd>{index + 1}</Kbd>
            </button>
          ))}
        </nav>
      </aside>

      <div className="relay-mobile-nav" aria-label="Mobile navigation">
        {navItems.slice(0, 5).map((item) => (
          <button key={item.path} type="button" aria-label={item.label} aria-current={current?.path === item.path ? 'page' : undefined} onClick={() => go(item.path)}>
            <span aria-hidden="true">{item.glyph}</span><small>{item.label}</small>
          </button>
        ))}
        <button type="button" aria-label="More controls" onClick={() => setStageOpen(true)}><span aria-hidden="true">···</span><small>More</small></button>
      </div>

      <div className="relay-app__main">
        {snapshotMode && (
          <div className="relay-snapshot-ribbon" role="status">
            <span><b>SAVED SNAPSHOT · NOT LIVE</b><small>Read-only replay · captured {new Date(snapshotCapturedAt).toLocaleString()}</small></span>
            <Button variant="ghost" size="small" onClick={leaveSnapshot}>Try live server</Button>
          </div>
        )}
        {current && location.pathname !== current.path && (
          <div className="relay-breadcrumb" aria-label="Breadcrumb">
            <button type="button" onClick={() => go(current.path)}>{current.label}</button>
            <span aria-hidden="true">/</span><span>{location.pathname.split('/').filter(Boolean).at(-1)}</span>
          </div>
        )}
        <Outlet />
      </div>

      <div className={`relay-shutter ${shutter ? 'is-closed' : ''}`} aria-hidden="true">
        <i /><i />
      </div>

      <CommandPalette
        open={paletteOpen}
        value={paletteQuery}
        commands={filteredCommands}
        onChange={setPaletteQuery}
        onClose={() => setPaletteOpen(false)}
        onRun={runCommand}
      />
      <StageControls open={stageOpen} onClose={() => setStageOpen(false)} onReset={resetDemo} />
      <PresenterStrip onNavigate={go} />
    </div>
    </RelayNavigationContext.Provider>
  )
}

function CommandPalette({ open, value, commands, onChange, onClose, onRun }) {
  const input = useRef(null)
  useEffect(() => {
    if (open) input.current?.focus()
  }, [open])
  if (!open) return null
  return (
    <div className="relay-command-overlay" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section className="relay-command" role="dialog" aria-modal="true" aria-label="Command palette">
        <label htmlFor="relay-command-input">COMMAND <Kbd>ESC</Kbd></label>
        <input id="relay-command-input" ref={input} value={value} onChange={(event) => onChange(event.target.value)} placeholder="Find a screen or action…" />
        <ul>
          {commands.map((command) => (
            <li key={command.label}><button type="button" onClick={() => onRun(command)}><span>{command.label}</span><small>{command.detail}</small></button></li>
          ))}
          {!commands.length && <li className="relay-command__empty">No matching command.</li>}
        </ul>
      </section>
    </div>
  )
}
