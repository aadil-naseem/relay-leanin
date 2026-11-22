import { useEffect, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiRequest } from '../api/client'
import { DataLabelBadge, WeatherSourceBadge } from '../components/domain'
import { Button, Dialog, Drawer, Segmented, Toggle } from '../components/primitives'
import { useUiStore } from '../store/ui'

const weatherModes = [
  { value: 'live', label: 'Live' },
  { value: 'replay', label: 'Replay' },
  { value: 'synthetic', label: 'Synthetic' },
]

export function StageControls({ open, onClose, onReset }) {
  const queryClient = useQueryClient()
  const snapshotMode = useUiStore((state) => state.snapshotMode)
  const modeQuery = useQuery({
    queryKey: ['demo-state'],
    queryFn: () => apiRequest('/demo/state'),
    staleTime: 15_000,
    enabled: open && !snapshotMode,
  })
  const weatherStatus = useQuery({
    queryKey: ['stage-weather'],
    queryFn: () => apiRequest('/factories/fac_owner/exposure'),
    staleTime: 15_000,
    enabled: open && !snapshotMode,
  })
  const health = useQuery({
    queryKey: ['health'],
    queryFn: () => apiRequest('/health'),
    staleTime: 15_000,
    enabled: open && !snapshotMode,
  })
  const [resetConfirm, setResetConfirm] = useState(false)
  const [modeError, setModeError] = useState(null)
  const modeMutation = useMutation({
    mutationFn: (weather) => apiRequest('/demo/mode', {
      method: 'POST',
      body: JSON.stringify({ weather }),
    }),
    onSuccess: async () => {
      setModeError(null)
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['demo-state'] }),
        queryClient.invalidateQueries({ queryKey: ['dashboard'] }),
        queryClient.invalidateQueries({ queryKey: ['exposure'] }),
        queryClient.invalidateQueries({ queryKey: ['stage-weather'] }),
      ])
    },
    onError: (error) => setModeError(error.message),
  })
  const resetMutation = useMutation({
    mutationFn: onReset,
    onSuccess: () => { setModeError(null); setResetConfirm(false); onClose() },
    onError: (error) => setModeError(error.message),
  })

  const highContrast = useUiStore((state) => state.highContrast)
  const reduceMotion = useUiStore((state) => state.reduceMotion)
  const sceneTier = useUiStore((state) => state.sceneTier)
  const backdrop = useUiStore((state) => state.backdrop)
  const sound = useUiStore((state) => state.sound)
  const presenterMode = useUiStore((state) => state.presenterMode)
  const setPreference = useUiStore((state) => state.setPreference)
  const mode = snapshotMode ? 'replay' : modeQuery.data?.weather_mode || 'replay'

  useEffect(() => {
    document.documentElement.dataset.contrast = highContrast ? 'high' : 'normal'
    document.documentElement.dataset.reduceMotion = reduceMotion ? 'true' : 'false'
    document.documentElement.dataset.sceneTier = sceneTier
    document.documentElement.dataset.backdrop = backdrop ? 'on' : 'off'
    return () => {
      delete document.documentElement.dataset.contrast
      delete document.documentElement.dataset.reduceMotion
      delete document.documentElement.dataset.sceneTier
      delete document.documentElement.dataset.backdrop
    }
  }, [highContrast, reduceMotion, sceneTier, backdrop])

  const handleReset = () => resetMutation.mutate()

  return (
    <>
      <Drawer open={open} title="Stage Controls" onClose={onClose} className="stage-controls-drawer">
        <div className="stage-controls">
          <section>
            <span className="f0-kicker">WEATHER MODE</span>
            <Segmented
              label="Weather mode"
              value={mode}
              options={weatherModes}
              disabled={snapshotMode}
              onChange={(nextMode) => modeMutation.mutate(nextMode)}
            />
            <div className="stage-controls__readout">
              {snapshotMode
                ? <span>SAVED REPLAY · NOT LIVE</span>
                : <WeatherSourceBadge
                  source={weatherStatus.data?.weather?.source || modeQuery.data?.weather_mode || mode}
                  degraded={Boolean(weatherStatus.data?.weather?.degraded)}
                />}
              <span>{modeQuery.data?.replay_event || 'michaung_2023'}</span>
              <DataLabelBadge />
            </div>
            {modeError && <p className="stage-controls__error" role="alert">{modeError}</p>}
          </section>

          <section>
            <span className="f0-kicker">DEMO DATA</span>
            <p>Rebuild the fictional sample world and clear generated demo state.</p>
            <Button variant="secondary" disabled={snapshotMode} onClick={() => setResetConfirm(true)}>Reset demo</Button>
          </section>

          <section>
            <span className="f0-kicker">SYSTEM READOUT</span>
            {snapshotMode ? <p>API · offline · snapshot data only</p> : !open || health.isLoading ? <p>Checking API health…</p> : health.isError || !health.data ? (
              <p className="stage-controls__error">Backend unavailable · {health.error.code}</p>
            ) : (
              <div className="stage-controls__health">
                <span>API · {health.data.status}</span>
                <span>DB · {health.data.db}</span>
                <span>Weather · {health.data.weather_mode}</span>
                {health.data.vision_chain.map((provider) => (
                  <span key={provider.provider}>{provider.provider} · {provider.configured ? 'ready' : 'off'}</span>
                ))}
              </div>
            )}
          </section>

          <section>
            <span className="f0-kicker">PRESENTER</span>
            <Toggle checked={presenterMode} onChange={(checked) => {
              setPreference('presenterMode', checked)
              if (checked) setPreference('presenterHidden', false)
            }} label="Presenter mode" />
            <p className="stage-controls__hint">Keyboard: → / ← steps · R resets · H hides the strip.</p>
          </section>

          <section>
            <span className="f0-kicker">PROJECTOR & MOTION</span>
            <Toggle checked={highContrast} onChange={(checked) => setPreference('highContrast', checked)} label="High contrast / projector" />
            <Toggle checked={reduceMotion} onChange={(checked) => setPreference('reduceMotion', checked)} label="Reduce motion" />
          </section>

          <section>
            <span className="f0-kicker">SCENE</span>
            <label className="stage-controls__select">3D quality
              <select value={sceneTier} onChange={(event) => setPreference('sceneTier', event.target.value)}>
                <option value="auto">Auto</option><option value="full">Full</option><option value="lite">Lite</option><option value="static">Static</option>
              </select>
            </label>
            <Toggle checked={backdrop} onChange={(checked) => setPreference('backdrop', checked)} label="Backdrop on" />
            <Toggle checked={sound} onChange={(checked) => setPreference('sound', checked)} label="Sound (off by default)" />
          </section>

          <section>
            <span className="f0-kicker">FAILURE FALLBACK</span>
            <Toggle checked={snapshotMode} onChange={(checked) => {
              queryClient.clear()
              setPreference('snapshotMode', checked)
            }} label="Snapshot mode" />
            <p className="stage-controls__hint">
              {snapshotMode ? 'Saved replay is active · backend writes are blocked.' : 'If the backend fails, open the saved replay snapshot.'}
            </p>
          </section>
        </div>
      </Drawer>
      <Dialog
        open={resetConfirm}
        title="Reset demo world?"
        onClose={() => setResetConfirm(false)}
        actions={<><Button variant="ghost" disabled={resetMutation.isPending} onClick={() => setResetConfirm(false)}>Cancel</Button><Button loading={resetMutation.isPending} onClick={handleReset}>Reset sample data</Button></>}
      >
        <p>This rebuilds the seeded sample data. It does not alter committed source or screenshots.</p>
        {modeError && <p className="stage-controls__error" role="alert">{modeError}</p>}
      </Dialog>
    </>
  )
}
