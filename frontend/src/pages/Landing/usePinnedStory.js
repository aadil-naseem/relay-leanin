import { useEffect } from 'react'

export function usePinnedStory({ trackRef, stageRef, enabled, onProgress, onNativePinFallback }) {
  useEffect(() => {
    if (!enabled || !trackRef.current || !stageRef.current) return undefined
    let cancelled = false
    let dispose = () => {}

    Promise.all([
      import('gsap'),
      import('gsap/ScrollTrigger'),
      import('lenis'),
    ]).then(([gsapModule, triggerModule, lenisModule]) => {
      if (cancelled) return
      const gsap = gsapModule.gsap || gsapModule.default
      const ScrollTrigger = triggerModule.ScrollTrigger || triggerModule.default
      const Lenis = lenisModule.default
      gsap.registerPlugin(ScrollTrigger)
      const lenis = new Lenis({
        autoRaf: false,
        smoothWheel: true,
        syncTouch: false,
        lerp: 0.075,
        wheelMultiplier: 0.85,
      })
      const tick = (time) => lenis.raf(time * 1000)
      lenis.on('scroll', ScrollTrigger.update)
      gsap.ticker.add(tick)
      gsap.ticker.lagSmoothing(0)
      const context = gsap.context(() => {
        ScrollTrigger.create({
          trigger: trackRef.current,
          start: 'top top',
          end: 'bottom bottom',
          pin: stageRef.current,
          pinSpacing: false,
          scrub: 1.1,
          invalidateOnRefresh: true,
          onUpdate: (self) => onProgress(self.progress),
        })
      }, trackRef.current)
      ScrollTrigger.refresh()
      onNativePinFallback(false)
      dispose = () => {
        context.revert()
        gsap.ticker.remove(tick)
        lenis.destroy()
      }
    }).catch(() => {
      if (cancelled) return
      onNativePinFallback(true)
      const update = () => {
        const track = trackRef.current
        if (!track) return
        const rect = track.getBoundingClientRect()
        const range = Math.max(1, track.offsetHeight - window.innerHeight)
        const progress = Math.max(0, Math.min(1, -rect.top / range))
        onProgress(progress)
      }
      window.addEventListener('scroll', update, { passive: true })
      update()
      dispose = () => window.removeEventListener('scroll', update)
    })

    return () => {
      cancelled = true
      dispose()
    }
  }, [enabled, onNativePinFallback, onProgress, stageRef, trackRef])
}
