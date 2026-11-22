import { useEffect, useState } from 'react'
import { useUiStore } from '../../store/ui'
import { chooseSceneTier } from '../../lib/sceneTier'

function supportsWebGL() {
  try {
    const canvas = document.createElement('canvas')
    return Boolean(canvas.getContext('webgl2') || canvas.getContext('webgl'))
  } catch {
    return false
  }
}

export function useSceneTier() {
  const preference = useUiStore((state) => state.sceneTier)
  const reduceMotion = useUiStore((state) => state.reduceMotion)
  const [environment, setEnvironment] = useState({
    ready: false,
    mobile: true,
    reducedMotion: true,
    webgl: false,
    cores: 0,
  })

  useEffect(() => {
    const mobile = window.matchMedia('(max-width: 760px)')
    const motion = window.matchMedia('(prefers-reduced-motion: reduce)')
    const webgl = supportsWebGL()
    const cores = navigator.hardwareConcurrency || 4
    const update = () => setEnvironment({
      ready: true,
      mobile: mobile.matches,
      reducedMotion: motion.matches || reduceMotion,
      webgl,
      cores,
    })
    update()
    mobile.addEventListener?.('change', update)
    motion.addEventListener?.('change', update)
    window.addEventListener('resize', update, { passive: true })
    return () => {
      mobile.removeEventListener?.('change', update)
      motion.removeEventListener?.('change', update)
      window.removeEventListener('resize', update)
    }
  }, [reduceMotion])

  const queryTier = new URLSearchParams(window.location.search).get('tier')
  return chooseSceneTier({
    requested: queryTier || preference,
    mobile: !environment.ready || environment.mobile,
    reducedMotion: reduceMotion || environment.reducedMotion,
    webgl: environment.ready && environment.webgl,
    cores: environment.cores,
  })
}
