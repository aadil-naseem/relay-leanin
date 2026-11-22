import { lazy, Suspense, useCallback, useEffect, useRef, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { apiRequest } from '../../api/client'
import { DataLabelBadge, Money, ReadinessRing, WeatherSourceBadge } from '../../components/domain'
import { Button, Nameplate, Stamp } from '../../components/primitives'
import { useUiStore } from '../../store/ui'
import { formatMoney } from '../../lib/format'
import { backupStatusLabel, exclusionReasonLabel } from '../../lib/status'
import backtest from '../../data/backtest.json'
import fallbackStory from '../../data/story.fallback.json'
import { chapterAt, localChapterProgress, STORY_CHAPTERS } from '../../lib/storyProgress'
import { useSceneTier } from './useSceneTier'
import { usePinnedStory } from './usePinnedStory'
import './landing.css'

const HeroScene = lazy(() => import('../../scene/HeroScene'))

export default function Landing() {
  const navigate = useNavigate()
  const tier = useSceneTier()
  const reduceMotion = useUiStore((state) => state.reduceMotion)
  const snapshotMode = useUiStore((state) => state.snapshotMode)
  const [performanceLimitedTier, setPerformanceLimitedTier] = useState(null)
  const [nativePinFallback, setNativePinFallback] = useState(false)
  const [progress, setProgress] = useState(0)
  const [pointer, setPointer] = useState({ x: 0, y: 0 })
  const [diving, setDiving] = useState(false)
  const pointerFrame = useRef(0)
  const diveTimer = useRef(0)
  const trackRef = useRef(null)
  const stageRef = useRef(null)

  const dashboard = useQuery({
    queryKey: ['dashboard', 'fac_owner'],
    queryFn: () => apiRequest('/dashboard/fac_owner'),
    staleTime: 30_000,
  })
  const stressId = dashboard.data?.alert?.stress_test_id
  const stress = useQuery({
    queryKey: ['stress-test', stressId],
    queryFn: () => apiRequest(`/stress-tests/${stressId}`),
    enabled: Boolean(stressId),
    staleTime: 30_000,
  })
  const demoState = useQuery({
    queryKey: ['demo-state'],
    queryFn: () => apiRequest('/demo/state'),
    staleTime: 30_000,
  })
  const matching = useQuery({
    queryKey: ['matching', 'hero-order', 'fac_owner'],
    queryFn: () => apiRequest('/matching/search', {
      method: 'POST',
      body: JSON.stringify({ order_id: 'ord_102' }),
    }),
    enabled: !dashboard.isError,
    staleTime: 30_000,
  })
  const actions = useQuery({
    queryKey: ['readiness', 'fac_owner', 'actions'],
    queryFn: () => apiRequest('/readiness/fac_owner/actions'),
    enabled: !dashboard.isError,
    staleTime: 30_000,
  })

  const showingFallback = dashboard.isError || (Boolean(stressId) && stress.isError)
  const spof = showingFallback ? fallbackStory.spof : dashboard.data?.spof_top?.[0]
  const summary = showingFallback ? fallbackStory.stress : stress.data?.summary
  const alert = showingFallback ? fallbackStory.alert : dashboard.data?.alert
  const weatherMode = showingFallback
    ? fallbackStory.weather_mode
    : dashboard.data?.weather?.mode || demoState.data?.weather_mode || 'replay'
  const weatherSource = showingFallback
    ? fallbackStory.weather_mode
    : dashboard.data?.weather?.source || weatherMode
  const replayEvent = (showingFallback
    ? fallbackStory.replay_event
    : demoState.data?.replay_event || 'michaung_2023').replaceAll('_', ' ').toUpperCase()
  const spofOrderCount = Array.isArray(spof?.orders_broken)
    ? spof.orders_broken.length
    : spof?.orders_broken
  const currentReadiness = showingFallback
    ? fallbackStory.readiness.weighted_score
    : dashboard.data?.readiness?.headline?.weighted ?? fallbackStory.readiness.weighted_score
  const projectedReadiness = showingFallback
    ? fallbackStory.readiness.projected_score
    : actions.data?.actions?.[0]?.projected_score ?? currentReadiness
  const readinessUplift = showingFallback
    ? fallbackStory.readiness.uplift_points
    : actions.data?.actions?.[0]?.uplift_points ?? projectedReadiness - currentReadiness
  const liveCandidates = matching.data?.candidates || []
  const storyPartners = matching.isError
    ? fallbackStory.partners
    : chooseStoryPartners(liveCandidates)
  const renderTier = performanceLimitedTier === tier && tier === 'full' ? 'lite' : tier
  const pinnedScene = renderTier === 'full' || renderTier === 'lite'
  const activeChapter = pinnedScene ? chapterAt(progress) : 0
  const pointerEnabled = !reduceMotion
    && !window.matchMedia('(prefers-reduced-motion: reduce)').matches
    && !window.matchMedia('(pointer: coarse)').matches

  const updateProgress = useCallback((value) => {
    setProgress(Math.round(value * 1000) / 1000)
  }, [])
  usePinnedStory({
    trackRef,
    stageRef,
    enabled: pinnedScene,
    onProgress: updateProgress,
    onNativePinFallback: setNativePinFallback,
  })

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'auto' })
  }, [])

  useEffect(() => () => {
    window.cancelAnimationFrame(pointerFrame.current)
    window.clearTimeout(diveTimer.current)
  }, [])

  const updatePointer = (event) => {
    if (!pointerEnabled || event.pointerType !== 'mouse') return
    const bounds = event.currentTarget.getBoundingClientRect()
    const nextPointer = {
      x: ((event.clientX - bounds.left) / bounds.width - 0.5) * 2,
      y: ((event.clientY - bounds.top) / bounds.height - 0.5) * 2,
    }
    window.cancelAnimationFrame(pointerFrame.current)
    pointerFrame.current = window.requestAnimationFrame(() => {
      setPointer(nextPointer)
      pointerFrame.current = 0
    })
  }

  const openDesk = () => {
    if (reduceMotion || window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      window.scrollTo({ top: 0, behavior: 'auto' })
      navigate('/app')
      return
    }
    setDiving(true)
    window.clearTimeout(diveTimer.current)
    diveTimer.current = window.setTimeout(() => {
      window.scrollTo({ top: 0, behavior: 'auto' })
      navigate('/app')
    }, 560)
  }
  const openProof = () => {
    window.scrollTo({ top: 0, behavior: 'auto' })
    navigate('/app/proof')
  }
  const jumpToChapter = (index) => {
    const behavior = reduceMotion ? 'auto' : 'smooth'
    if (renderTier === 'static') {
      const target = index === 0 ? document.getElementById('hero') : document.getElementById(`static-chapter-${index}`)
      const offset = document.querySelector('.landing-nav')?.offsetHeight || 0
      if (target) window.scrollTo({ top: target.getBoundingClientRect().top + window.scrollY - offset, behavior })
      return
    }
    const track = trackRef.current
    if (!track) return
    const scrollRange = Math.max(0, track.offsetHeight - window.innerHeight)
    const top = track.getBoundingClientRect().top + window.scrollY
    window.scrollTo({
      top: top + scrollRange * STORY_CHAPTERS[index].start,
      behavior,
    })
  }

  return (
    <main className="landing-page">
      <LandingNav
        snapshotMode={snapshotMode}
        onStory={() => jumpToChapter(0)}
        onHow={() => scrollPageTo('how-it-works', reduceMotion)}
        onProof={() => scrollPageTo('landing-proof', reduceMotion)}
        onOpenDesk={openDesk}
      />

      {pinnedScene ? (
        <div className="landing-story-track" id="story-stage" ref={trackRef}>
          <div className={`landing-story-pin ${nativePinFallback ? 'is-native-pin' : ''}`} ref={stageRef}>
            <HeroStage
              tier={renderTier}
              chapter={activeChapter}
              progress={progress}
              pointer={pointer}
              pointerEnabled={pointerEnabled}
              spof={spof}
              spofOrderCount={spofOrderCount}
              summary={summary}
              alert={alert}
              currentReadiness={currentReadiness}
              projectedReadiness={projectedReadiness}
              readinessUplift={readinessUplift}
              partners={storyPartners}
              partnersLoading={matching.isLoading}
              fallback={showingFallback}
              weatherMode={weatherMode}
              weatherSource={weatherSource}
              replayEvent={replayEvent}
              onPointerMove={updatePointer}
              onPointerLeave={() => setPointer({ x: 0, y: 0 })}
              onPerformanceDecline={() => setPerformanceLimitedTier(tier)}
              onChapterSelect={jumpToChapter}
              onOpenDesk={openDesk}
            />
          </div>
        </div>
      ) : (
        <section className="landing-static-story" id="story-stage">
          <HeroStage
            tier="static"
            chapter={0}
            progress={0}
            pointer={pointer}
            pointerEnabled={pointerEnabled}
            spof={spof}
            spofOrderCount={spofOrderCount}
            summary={summary}
            alert={alert}
            currentReadiness={currentReadiness}
            projectedReadiness={projectedReadiness}
            readinessUplift={readinessUplift}
            partners={storyPartners}
            partnersLoading={matching.isLoading}
            fallback={showingFallback}
            weatherMode={weatherMode}
            weatherSource={weatherSource}
            replayEvent={replayEvent}
            onPointerMove={updatePointer}
            onPointerLeave={() => setPointer({ x: 0, y: 0 })}
            onChapterSelect={jumpToChapter}
            onOpenDesk={openDesk}
          />
          {STORY_CHAPTERS.slice(1).map((chapter, index) => (
            <StaticChapter
              key={chapter.label}
              index={index + 1}
              currentScore={currentReadiness}
              projectedScore={projectedReadiness}
              uplift={readinessUplift}
              partners={storyPartners}
              spof={spof}
              spofOrderCount={spofOrderCount}
              alert={alert}
              summary={summary}
              partnersLoading={matching.isLoading}
              fallback={showingFallback}
            />
          ))}
        </section>
      )}

      <HowItWorks />
      <ProofSection onOpenProof={openProof} />
      <HonestLimits />
      <FinalCta onOpenDesk={openDesk} />
      <Footer />
      <div className={`landing-dive ${diving ? 'is-active' : ''}`} aria-hidden="true" />
    </main>
  )
}

function scrollPageTo(id, reduceMotion) {
  const target = document.getElementById(id)
  const offset = document.querySelector('.landing-nav')?.offsetHeight || 0
  if (target) window.scrollTo({
    top: target.getBoundingClientRect().top + window.scrollY - offset,
    behavior: reduceMotion ? 'auto' : 'smooth',
  })
}

function LandingNav({ snapshotMode, onStory, onHow, onProof, onOpenDesk }) {
  return (
    <>
      <header className="landing-nav">
        <button className="landing-nav__brand" type="button" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}>
          RELAY <span>FACTORY CONTINUITY DESK</span>
        </button>
        <nav aria-label="Landing navigation">
          <button type="button" onClick={onStory}>Story</button>
          <button type="button" onClick={onHow}>How it works</button>
          <button type="button" onClick={onProof}>Proof</button>
        </nav>
        <Button onClick={onOpenDesk}>Open the desk <span aria-hidden="true">↗</span></Button>
      </header>
      {snapshotMode && (
        <div className="landing-snapshot-ribbon" role="status">
          <b>SAVED SNAPSHOT · NOT LIVE</b><span>Read-only replay</span>
          <button type="button" onClick={onOpenDesk}>Open saved Desk ↗</button>
        </div>
      )}
    </>
  )
}

function HeroStage({
  tier, chapter, progress, pointer, pointerEnabled,
  spof, spofOrderCount, summary, alert,
  currentReadiness, projectedReadiness, readinessUplift,
  partners, partnersLoading, fallback, weatherMode, weatherSource, replayEvent,
  onPointerMove, onPointerLeave, onPerformanceDecline, onChapterSelect, onOpenDesk,
}) {
  const threatProgress = localChapterProgress(progress, 2)
  const activeCopy = getChapterCopy(chapter, {
    spof, spofOrderCount, summary, alert, currentReadiness, projectedReadiness, readinessUplift,
  })

  return (
    <section
      className="landing-hero"
      id={tier === 'static' ? 'hero' : undefined}
      data-tier={tier}
      data-chapter={chapter}
      onPointerMove={onPointerMove}
      onPointerLeave={onPointerLeave}
      style={{
        '--headline-x': `${-pointer.x * 14}px`,
        '--headline-y': `${-pointer.y * 8}px`,
        '--rain-opacity': `${tier === 'static' ? 0.11 : 0.12 + threatProgress * 0.3}`,
      }}
      aria-labelledby="landing-title"
    >
      <div className="landing-sky" aria-hidden="true" />
      <Skyline />
      <div className="landing-headline">
        <h1 id="landing-title">FIND WHERE YOU BREAK</h1>
      </div>
      <StaticYard chapter={chapter} />
      {(tier === 'full' || tier === 'lite') && (
        <div className="landing-canvas" aria-hidden="true">
          <Suspense fallback={null}>
            <HeroScene
              tier={tier}
              pointer={pointerEnabled ? pointer : { x: 0, y: 0 }}
              progress={progress}
              partners={partners}
              onDecline={onPerformanceDecline}
            />
          </Suspense>
        </div>
      )}
      <div className="landing-rain" aria-hidden="true" />
      {chapter === 0 ? (
        <p className="landing-headline__front">before the flood does.</p>
      ) : (
        <div className="landing-chapter-copy" aria-live="polite">
          <span>{String(chapter).padStart(2, '0')} / {STORY_CHAPTERS[chapter].label}</span>
          <h2>{activeCopy.title}</h2>
          <p>{activeCopy.body}</p>
        </div>
      )}

      {chapter === 0 && (
        <>
          <WeakPointCallout
            spof={spof}
            orderCount={spofOrderCount}
            onOpenDesk={onOpenDesk}
            onWatch={() => onChapterSelect(1)}
          />
          <ExposureCallout
            alert={alert}
            summary={summary}
            fallback={fallback}
            weatherSource={weatherSource}
          />
        </>
      )}
      {chapter === 1 && (
        <div className="landing-chapter-insight landing-chapter-insight--left">
          <span className="f0-kicker">SPOF · REMOVE ONE RESOURCE</span>
          <strong>{spof?.name || 'Sample resource'}</strong>
          <span>{spofOrderCount || '—'} orders · {spof ? formatMoney(spof.revenue_at_risk_inr) : 'revenue at risk'}</span>
        </div>
      )}
      {chapter === 2 && (
        <div className="landing-chapter-insight landing-chapter-insight--right">
          <span className="f0-kicker">AUTO TEST · REPLAY</span>
          <strong>{summary ? `${summary.orders_at_risk} orders · ${formatMoney(summary.revenue_exposed_inr)}` : 'Stress summary unavailable'}</strong>
          <span>Scroll scrubs the scene, not an hourly chart; the current API has no rain time-series.</span>
        </div>
      )}
      {chapter === 3 && (
        <RelayPanel partners={partners} loading={partnersLoading} compact />
      )}
      {chapter === 4 && (
        <ReadyPanel
          currentScore={currentReadiness}
          projectedScore={projectedReadiness}
          uplift={readinessUplift}
          fallback={fallback}
        />
      )}

      {chapter === 2 && (
        <div className="landing-story-horizon" aria-label="Illustrative 72 hour story horizon">
          <span>T+00</span><i><b style={{ left: `${threatProgress * 100}%` }} /></i><span>T+72</span>
          <small>ILLUSTRATIVE STORY SCRUB · NOT AN HOURLY FORECAST CHART</small>
        </div>
      )}

      <ChapterRail active={chapter} onSelect={onChapterSelect} />
      <div className="landing-source-line">
        <span>CHENNAI · {replayEvent}</span>
        <span>{fallback ? 'SAVED REPLAY · NOT LIVE' : `${weatherMode.toUpperCase()} MODE`}</span>
        <span>{fallback ? `LAST VERIFIED ${new Date(fallbackStory.captured_at_utc).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', timeZone: 'UTC' })}` : 'SAMPLE / SIMULATED'}</span>
      </div>
      <button
        className="landing-scroll-cue"
        type="button"
        onClick={() => chapter < 4 ? onChapterSelect(chapter + 1) : onOpenDesk()}
      >
        <span aria-hidden="true">↓</span> {chapter < 4 ? 'SCROLL TO FOLLOW THE STORY' : 'OPEN THE DESK'}
      </button>
      <div className="landing-tier-label" aria-label={`Scene quality ${tier}`}>
        SCENE TIER · {tier.toUpperCase()}
      </div>
      <Stamp tone="gold" className="landing-sample-stamp">SAMPLE / SIMULATED</Stamp>
    </section>
  )
}

function WeakPointCallout({ spof, orderCount, onOpenDesk, onWatch }) {
  return (
    <aside className="landing-callout landing-callout--weak" aria-label="Top single point of failure">
      <span className="f0-kicker">THE SINGLE BREAK · {spof?.kind?.toUpperCase() || 'SAMPLE RESOURCE'}</span>
      {spof ? (
        <>
          <h2>{spof.name}</h2>
          <p><b>{orderCount} {orderCount === 1 ? 'order depends' : 'orders depend'}</b> on this resource.</p>
          <div className="landing-callout__value"><Money value={spof.revenue_at_risk_inr} /><small>at risk if it stops</small></div>
        </>
      ) : <p className="landing-loading">Checking the replay sample…</p>}
      <div className="landing-callout__actions">
        <Button onClick={onOpenDesk}>Open the desk</Button>
        <Button variant="ghost" onClick={onWatch}>Watch the story</Button>
      </div>
    </aside>
  )
}

function ExposureCallout({ alert, summary, fallback, weatherSource }) {
  return (
    <aside className="landing-callout landing-callout--exposure" aria-label="Current replay exposure">
      <div className="landing-callout__meta">
        <span className="f0-kicker">STORM WINDOW</span>
        {fallback
          ? <Nameplate>SAVED REPLAY · NOT LIVE</Nameplate>
          : <WeatherSourceBadge source={weatherSource} degraded={false} />}
      </div>
      {alert?.active ? (
        <>
          <h2>{alert.onset_in_hours == null ? 'Rain alert active' : `Heavy rain in ${Math.round(alert.onset_in_hours)} h`}</h2>
          {summary ? (
            <div className="landing-callout__exposure">
              <Money value={summary.revenue_exposed_inr} />
              <span>{summary.orders_at_risk} orders at risk</span>
            </div>
          ) : <p className="landing-loading">Loading the auto stress test…</p>}
        </>
      ) : <h2>No active rain alert</h2>}
      <p className="landing-callout__fine">RISK INDICATOR · NOT A FLOOD MODEL</p>
      <DataLabelBadge />
    </aside>
  )
}

function ChapterRail({ active, onSelect }) {
  return (
    <nav className="landing-chapter-rail" aria-label="Story chapters">
      <ol>
        {STORY_CHAPTERS.map((chapter, index) => (
          <li key={chapter.label} className={active === index ? 'is-active' : ''}>
            <button type="button" aria-current={active === index ? 'step' : undefined} onClick={() => onSelect(index)}>
              <span>{String(index).padStart(2, '0')}</span><b>{chapter.label}</b>
            </button>
          </li>
        ))}
      </ol>
    </nav>
  )
}

function RelayPanel({ partners, loading, compact = false }) {
  return (
    <section className={`landing-relay-panel ${compact ? 'is-compact' : ''}`} aria-label="Sample backup partner states">
      <span className="f0-kicker">CANDIDATE COVER · SAME EVENT</span>
      {loading && !partners.length ? <p>Checking partner options…</p> : !partners.length ? (
        <p>No candidates returned for this sample order.</p>
      ) : (
        <ul>
          {partners.map((partner) => (
            <li className={`is-${String(partner.status || 'POTENTIAL_MATCH').toLowerCase()}`} key={`${partner.name}-${partner.status}`}>
              <i aria-hidden="true" />
              <span>{partner.name}</span>
              <b>{backupStatusLabel(partner.status)}</b>
              {partner.reason && <small>Excluded · {exclusionReasonLabel(partner.reason)}</small>}
            </li>
          ))}
        </ul>
      )}
      <small>Matches are candidates, not approved backups.</small>
    </section>
  )
}

function ReadyPanel({ currentScore, projectedScore, uplift, fallback }) {
  return (
    <section className="landing-ready-panel" aria-label="Recovery readiness counterfactual">
      <span className="f0-kicker">M8 · 48-HOUR WEIGHTED COVERAGE</span>
      <ReadinessRing score={projectedScore} weighted={currentScore} size={112} />
      <strong>{currentScore.toFixed(1)} <i>→</i> {projectedScore.toFixed(1)}</strong>
      <p>{uplift.toFixed(1)} point counterfactual · projected if the next-best checks are closed.</p>
      {fallback && <Nameplate>SAVED REPLAY · NOT LIVE</Nameplate>}
    </section>
  )
}

function StaticChapter({ index, currentScore, projectedScore, uplift, partners, spof, spofOrderCount, alert, summary, partnersLoading, fallback }) {
  const copy = getChapterCopy(index, {
    spof, spofOrderCount, summary, alert, currentReadiness: currentScore,
    projectedReadiness: projectedScore, readinessUplift: uplift,
  })
  return (
    <section className="landing-static-chapter" id={`static-chapter-${index}`} aria-labelledby={`static-chapter-title-${index}`}>
      <div className="landing-static-chapter__art" aria-hidden="true">
        <StaticIllustration index={index} />
      </div>
      <div className="landing-static-chapter__copy">
        <span className="f0-kicker">{String(index).padStart(2, '0')} / {STORY_CHAPTERS[index].label}</span>
        <h2 id={`static-chapter-title-${index}`}>{copy.title}</h2>
        <p>{copy.body}</p>
        {index === 1 && spof && (
          <Nameplate>{spof.name} · {spofOrderCount} orders · {formatMoney(spof.revenue_at_risk_inr)}</Nameplate>
        )}
        {index === 2 && summary && (
          <div className="landing-static-metrics"><b>{formatMoney(summary.revenue_exposed_inr)}</b><span>{summary.orders_at_risk} orders at risk</span></div>
        )}
        {index === 3 && <RelayPanel partners={partners} loading={partnersLoading} />}
        {index === 4 && <ReadyPanel currentScore={currentScore} projectedScore={projectedScore} uplift={uplift} fallback={fallback} />}
      </div>
    </section>
  )
}

function StaticIllustration({ index }) {
  return (
    <svg viewBox="0 0 560 280" role="img" aria-label={['Lit factory bay', 'Dependency links to one resource', 'Illustrative rain and hazard zone', 'Schematic backup network', 'Readiness ring'][index]}>
      <path className="landing-static-illustration__ground" d="M0 198 280 92l280 106v82H0Z" />
      {index === 1 && (
        <g className="landing-static-illustration__links">
          <path d="M92 78h142v90m-142-45h142m0 45h92" />
          <circle cx="92" cy="78" r="10" /><circle cx="92" cy="123" r="10" /><circle cx="92" cy="168" r="10" />
          <rect x="326" y="140" width="102" height="58" />
        </g>
      )}
      {index === 2 && (
        <g className="landing-static-illustration__storm">
          <path d="m100 54-18 42m73-42-18 42m73-42-18 42m73-42-18 42m73-42-18 42m73-42-18 42m73-42-18 42" />
          <path d="M106 154q33-48 67 0t67 0t67 0t67 0t67 0" />
          <circle cx="278" cy="171" r="42" />
        </g>
      )}
      {index === 3 && (
        <g className="landing-static-illustration__relay">
          <path d="M111 144 260 90l176 77M111 144l176 80 149-57" />
          <circle cx="111" cy="144" r="16" /><circle cx="260" cy="90" r="14" />
          <circle cx="436" cy="167" r="14" /><circle cx="287" cy="224" r="12" />
        </g>
      )}
      {index === 4 && (
        <g className="landing-static-illustration__ready">
          <circle cx="280" cy="135" r="82" />
          <path d="M280 53a82 82 0 0 1 78 57" />
          <path d="M370 93v28h-28" />
        </g>
      )}
      {index === 0 && (
        <g className="landing-static-illustration__bay">
          <path d="m180 111 50-27 54 27v67l-54 29-50-29z" />
          <path d="m230 84 52 27 52-27-53-28z" />
          <rect x="238" y="129" width="29" height="48" />
          <circle cx="251" cy="155" r="68" />
        </g>
      )}
    </svg>
  )
}

function HowItWorks() {
  const cards = [
    ['01', 'Read the drawing', 'Build a Production Passport from process, material, tolerances and inspection notes.'],
    ['02', 'Find the break', 'Trace the orders that lose a required machine, vendor or material.'],
    ['03', 'Watch the sky', 'Combine rain and site conditions into a risk indicator—not a flood prediction.'],
    ['04', 'Line up cover', 'Compare capable partners, their declared readiness and correlated risk.'],
  ]
  return (
    <section className="landing-after landing-how" id="how-it-works" aria-labelledby="landing-how-title">
      <div className="landing-section-head">
        <span className="f0-kicker">FROM DRAWING TO CONTINUITY</span>
        <h2 id="landing-how-title">HOW IT WORKS</h2>
      </div>
      <div className="landing-work-grid">
        {cards.map(([number, title, body], index) => (
          <article className="landing-work-card" key={number}>
            <span>{number}</span><b>{index < cards.length - 1 ? '→' : '↗'}</b>
            <h3>{title}</h3><p>{body}</p>
          </article>
        ))}
      </div>
      <p className="landing-work-claim">Our software reads the drawing. Our maths tells you where you break.</p>
    </section>
  )
}

function ProofSection({ onOpenProof }) {
  return (
    <section className="landing-after landing-proof" id="landing-proof" aria-labelledby="landing-proof-title">
      <div className="landing-section-head">
        <span className="f0-kicker">M4 · CYCLONE MICHAUNG · CHENNAI</span>
        <h2 id="landing-proof-title">TESTED ON A REAL STORM</h2>
        <p>Seven curated sites · lowest reported-flooded score 70 · highest not flooded 48 · +22 points.</p>
      </div>
      <div className="landing-proof-list">
        {backtest.sites.map((site, index) => (
          <div className={`landing-proof-row ${site.label === 'FLOODED' ? 'is-flooded' : ''}`} key={site.site}>
            <span>{String(index + 1).padStart(2, '0')}</span>
            <b>{site.site}</b>
            <i>{site.label === 'FLOODED' ? '●' : '○'}</i>
            <div><span style={{ width: `${site.risk}%` }} /></div>
            <strong>{site.risk}</strong>
          </div>
        ))}
      </div>
      <p className="landing-proof-note">Risk indicator from historical rain and site conditions; not a flood model or forecast guarantee.</p>
      <Button variant="ghost" onClick={onOpenProof}>Read the method →</Button>
    </section>
  )
}

function HonestLimits() {
  return (
    <section className="landing-after landing-limits" aria-labelledby="landing-limits-title">
      <span className="f0-kicker">HONEST LIMITS</span>
      <h2 id="landing-limits-title">CLEAR EYES. BETTER DECISIONS.</h2>
      <div>
        <p>Risk is an indicator, not a prediction.</p>
        <p>Matches are candidates, not approved backups.</p>
        <p>Factories and orders shown are fictional samples.</p>
      </div>
    </section>
  )
}

function FinalCta({ onOpenDesk }) {
  return (
    <section className="landing-final-cta">
      <span className="landing-final-cta__bay" aria-hidden="true"><i /></span>
      <div><span className="f0-kicker">CONTINUITY STARTS BEFORE THE STORM</span><h2>KNOW YOUR COVER.</h2></div>
      <Button onClick={onOpenDesk}>Open the desk <span aria-hidden="true">↗</span></Button>
    </section>
  )
}

function Footer() {
  return (
    <footer className="landing-footer">
      <span>RELAY · FACTORY CONTINUITY DESK</span>
      <span><a href="https://open-meteo.com/" target="_blank" rel="noreferrer">Weather data by Open-Meteo.com</a> · <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">© OpenStreetMap contributors</a></span>
      <span>FICTIONAL SAMPLE WORLD · CONTINUITY HACKATHON</span>
      <a href="https://github.com/aadil-naseem/project-relay" target="_blank" rel="noreferrer">REPOSITORY ↗</a>
    </footer>
  )
}

function getChapterCopy(chapter, data) {
  if (chapter === 1) {
    return {
      title: `${data.spof?.name || 'One resource'} is the break.`,
      body: `${data.spofOrderCount || '—'} routed orders rely on this resource. Removing it leaves those requirements without a baseline alternative.`,
    }
  }
  if (chapter === 2) {
    const onset = data.alert?.onset_in_hours
    return {
      title: onset == null ? 'The storm reaches the footprint.' : `Heavy rain in ${Math.round(onset)} hours.`,
      body: data.summary
        ? `${data.summary.orders_at_risk} orders at risk · ${formatMoney(data.summary.revenue_exposed_inr)} exposed. Scene progression is illustrative; hourly samples are not in the dashboard response.`
        : 'The sample stress result is unavailable; the risk indicator is not a flood model.',
    }
  }
  if (chapter === 3) {
    return {
      title: 'Cover beyond the same water.',
      body: 'A capable partner still needs a fresh READY status and must not share the same disruption risk.',
    }
  }
  return {
    title: 'Know your cover before you need it.',
    body: `Weighted readiness ${data.currentReadiness.toFixed(1)} → ${data.projectedReadiness.toFixed(1)} in the 48-hour sample counterfactual.`,
  }
}

function chooseStoryPartners(candidates) {
  if (!candidates.length) return []
  const ready = candidates.find((candidate) => !candidate.excluded && candidate.effective_status === 'READY')
  const pending = candidates.find((candidate) => !candidate.excluded && candidate.effective_status === 'APPROVAL_PENDING')
  const stale = candidates.find((candidate) => !candidate.excluded && candidate.effective_status === 'STALE')
  const excluded = candidates.find(
    (candidate) => candidate.excluded && ['SAME_CLUSTER', 'SAME_HAZARD_ZONE'].includes(candidate.exclusion_reason),
  ) || candidates.find((candidate) => candidate.excluded)
  return [ready, pending, stale, excluded].filter(Boolean).map((candidate) => ({
    name: candidate.name,
    status: candidate.excluded ? 'EXCLUDED' : candidate.effective_status || candidate.status,
    reason: candidate.exclusion_reason,
  }))
}

function Skyline() {
  return (
    <svg className="landing-skyline" viewBox="0 0 1600 520" preserveAspectRatio="xMidYMax slice" aria-hidden="true">
      <path className="landing-skyline__far" d="M0 312h70v-74h42v30h44v-93h37v36h42v101h48v-65h32v-97h36v31h36v131h61v-86h51v44h38v-127h36v28h36v141h63v-69h43v-34h44v103h65v-118h34v-59h42v39h48v138h58v-80h44v24h43v-133h38v38h44v151h73v-103h43v35h58v-89h43v36h57v123h69v-141h41v65h51v76h44v-52h66v52H0Z" />
      <path className="landing-skyline__near" d="M0 365h108v-50h69v50h98v-79h51v30h83v49h94v-63h62v63h89v-97h54v37h69v60h116v-74h49v32h67v42h83v-52h67v52h83v-84h53v30h61v54h112v-65h58v65h97v-42h54v42h86v155H0Z" />
      <g className="landing-skyline__lines">
        <path d="M274 315v-75m0 20-33-18m33 37 37-26M836 268v-85m0 30-36-21m36 41 38-24M1260 311v-65m0 21-34-19m34 37 31-24" />
        <path d="M285 240h-20m581-57h-22m427 63h-18" />
      </g>
    </svg>
  )
}

function StaticYard({ chapter = 0 }) {
  const buildings = [
    { x: 95, y: 285, scale: 0.48 }, { x: 292, y: 275, scale: 0.53 }, { x: 510, y: 270, scale: 0.56 },
    { x: 795, y: 274, scale: 0.54 }, { x: 1032, y: 282, scale: 0.50 }, { x: 1278, y: 289, scale: 0.46 },
    { x: 36, y: 364, scale: 0.63 }, { x: 238, y: 354, scale: 0.69 }, { x: 445, y: 350, scale: 0.74 },
    { x: 747, y: 349, scale: 0.72, lit: true }, { x: 1017, y: 354, scale: 0.68 }, { x: 1275, y: 365, scale: 0.62 },
    { x: 130, y: 434, scale: 0.82 }, { x: 404, y: 424, scale: 0.88 }, { x: 1005, y: 427, scale: 0.86 },
  ]

  return (
    <svg className="landing-yard" data-chapter={chapter} viewBox="0 0 1600 600" preserveAspectRatio="xMidYMax slice" aria-hidden="true">
      <defs>
        <radialGradient id="landing-bay-glow">
          <stop offset="0" stopColor="var(--c-sun)" stopOpacity=".42" />
          <stop offset="1" stopColor="var(--c-sun)" stopOpacity="0" />
        </radialGradient>
      </defs>
      <path className="landing-yard__ground" d="M0 425 800 220l800 205v175H0Z" />
      <path className="landing-yard__perspective" d="M800 220 0 600m800-380 270 380m-270-380 800 380M0 466h1600M0 522h1600M0 567h1600" />
      {buildings.map((building) => (
        <g
          key={`${building.x}-${building.y}`}
          className={`landing-bay ${building.lit ? 'is-lit' : ''}`}
          transform={`translate(${building.x} ${building.y}) scale(${building.scale})`}
        >
          {building.lit && <ellipse className="landing-bay__glow" cx="74" cy="81" rx="156" ry="115" fill="url(#landing-bay-glow)" />}
          <path className="landing-bay__side" d="M0 26 78 0v103l-78 30Z" />
          <path className="landing-bay__face" d="M78 0 156 26v103l-78-26Z" />
          <path className="landing-bay__roof" d="M0 26 28 3l25 16 25-19 26 19 25-18 27 25-78-26Z" />
          <path className="landing-bay__seams" d="M14 25v97m22-104v98m47-85v83m25-75v78m25-72v81" />
          <rect className="landing-bay__door" x="97" y="49" width="37" height="55" />
          <path className="landing-bay__doorline" d="M103 54v45m7-45v45m7-45v45m7-45v45m7-45v45" />
          <path className="landing-bay__window" d="M17 54h41v21H17z" />
          <path className="landing-bay__light" d="M20 58h35v13H20z" />
        </g>
      ))}
      <g className="landing-yard__crane">
        <path d="M473 243V80h452v163M470 80h464m-247 0v91m-16 0h32m-25 0v69" />
        <path className="landing-yard__hook" d="M678 240v22q0 17 13 17t13-17v-10" />
        <path className="landing-yard__trolley" d="M656 75h49v16h-49z" />
      </g>
      <circle className="landing-yard__anchor" cx="820" cy="421" r="6" />
    </svg>
  )
}
