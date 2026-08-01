'use client'

import { useEffect, useLayoutEffect } from 'react'
import dynamic from 'next/dynamic'
import Lenis from 'lenis'
import gsap from 'gsap'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { PortfolioHeader }       from "@/components/landing/Header"
import { PortfolioHero }          from "@/components/landing/Hero"
import { PortfolioSelectedWorks } from "@/components/landing/SelectedWorks"
import { PortfolioAbout }         from "@/components/landing/About"
import { PortfolioClientLogos }   from "@/components/landing/ClientLogos"
import { PortfolioTestimonials }  from "@/components/landing/Testimonials"
import { PortfolioAwards }        from "@/components/landing/Awards"
import { PortfolioInsights }      from "@/components/landing/Insights"
import { PortfolioFinalCTA }      from "@/components/landing/FinalCTA"
import { PortfolioFooter }        from "@/components/landing/Footer"
import { GradientBar }            from "@/components/ui/gradient-bar"
import { ScrollProgress }         from "@/components/ui/scroll-progress"
import { InlineLoader }           from "@/components/shared/BrandedLoader"

const PortfolioHowItWorks = dynamic(
  () => import("@/components/landing/HowItWorks").then(m => ({ default: m.PortfolioHowItWorks })),
  {
    ssr: false,
    loading: () => (
      <div
        id="how-it-works"
        style={{
          height: "100vh",
          background: "var(--cx-section-bg, rgba(15,17,23,0.60))",
          backdropFilter: "saturate(180%) blur(20px)",
          WebkitBackdropFilter: "saturate(180%) blur(20px)",
          borderTop: "1px solid var(--cx-card-border, rgba(255,255,255,0.09))",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <InlineLoader stage="loading" message="Loading…" size={32} />
      </div>
    ),
  },
)

// ── Register GSAP plugins ─────────────────────────────────────────────────────
gsap.registerPlugin(ScrollTrigger)

// ── Lenis smooth scroll — bridged to GSAP ticker ─────────────────────────────
// Requirements 16.2, 16.3, 16.4, 16.7
// Replace internal RAF loop with GSAP ticker so all ScrollTrigger timelines
// read from the same tick, eliminating Scroll_Jitter.
function useLenis() {
  useLayoutEffect(() => {
    const lenis = new Lenis({
      duration: 0.9,
      easing: (t: number) => 1 - Math.pow(1 - t, 3),   // cubic ease-out
      orientation: "vertical",
      smoothWheel: true,
      wheelMultiplier: 1.0,   // 1:1 on wheel, no artificial slowdown
      touchMultiplier: 1.5,
      infinite: false,
    })

    // Req 16.3 — keep ScrollTrigger in sync with Lenis scroll position
    // Store the callback reference so it can be cleanly removed on unmount
    const scrollCallback = () => ScrollTrigger.update()
    lenis.on('scroll', scrollCallback)

    // Req 16.2 — drive Lenis via GSAP ticker instead of a raw RAF loop
    const tickerCallback = (time: number) => lenis.raf(time * 1000)
    gsap.ticker.add(tickerCallback)

    // Disable GSAP lag smoothing so the ticker fires every frame without
    // skipping, preventing jitter during rapid scrolling.
    gsap.ticker.lagSmoothing(0)

    // Req 16.7 — hash-scroll after all components mount
    // Use a small timeout to ensure every child component has rendered before
    // we attempt to resolve the target element.
    const hashTimer = setTimeout(() => {
      const hash = window.location.hash
      if (hash) {
        const el = document.querySelector(hash) as HTMLElement | null
        if (el) {
          lenis.scrollTo(el, { offset: -80 })
        }
      }
    }, 100)

    // Req 16.4 — remove ticker callback and destroy Lenis on unmount
    return () => {
      clearTimeout(hashTimer)
      lenis.off('scroll', scrollCallback)
      gsap.ticker.remove(tickerCallback)
      lenis.destroy()
    }
  }, [])
}

// ── Scroll-reveal (IntersectionObserver) ─────────────────────────────────────
// Deferred so all child components are in the DOM before we query for
// [data-reveal] and [data-stagger] attributes.
function useScrollReveal() {
  useEffect(() => {
    let idleId: number | undefined
    let timeoutId: ReturnType<typeof setTimeout> | undefined

    const setup = () => {
      const els = document.querySelectorAll('[data-reveal], [data-stagger]')
      const io = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              entry.target.classList.add('revealed')
              io.unobserve(entry.target)
            }
          })
        },
        { threshold: 0.08, rootMargin: '0px 0px -32px 0px' },
      )
      els.forEach((el) => io.observe(el))
      return () => io.disconnect()
    }

    let teardown: (() => void) | undefined

    if (typeof requestIdleCallback !== 'undefined') {
      idleId = requestIdleCallback(() => { teardown = setup() }, { timeout: 2000 })
    } else {
      timeoutId = setTimeout(() => { teardown = setup() }, 300)
    }

    return () => {
      if (idleId !== undefined) cancelIdleCallback(idleId)
      if (timeoutId !== undefined) clearTimeout(timeoutId)
      teardown?.()
    }
  }, [])
}

// ── Mouse spotlight — very subtle radial gradient follows cursor ──────────────
// Soft, low-opacity page-level light that makes the page feel alive.
// Deliberately understated: 220px radius, 0.05 opacity max.
function useMouseSpotlight() {
  useEffect(() => {
    if (!window.matchMedia('(pointer: fine)').matches) return

    const el = document.createElement('div')
    el.setAttribute('data-mouse-spotlight', '')
    el.style.cssText = [
      'position:fixed',
      'inset:0',
      'pointer-events:none',
      'z-index:0',
      // Smaller, dimmer gradient — 220px, 0.05 opacity max
      'background:radial-gradient(220px circle at var(--sx,50%) var(--sy,50%),rgba(0,0,0,0.035) 0%,transparent 70%)',
      'opacity:0',
      'transition:opacity 400ms ease',
    ].join(';')
    document.body.insertBefore(el, document.body.firstChild)

    let cx = 0, cy = 0, tx = 0, ty = 0
    let rafId: number
    let running = false

    function tick() {
      // Tighter lerp (0.12) — follows cursor more responsively, less slug
      cx += (tx - cx) * 0.12
      cy += (ty - cy) * 0.12
      el.style.setProperty('--sx', `${cx}px`)
      el.style.setProperty('--sy', `${cy}px`)
      rafId = requestAnimationFrame(tick)
    }

    function startRAF() {
      if (!running) { running = true; rafId = requestAnimationFrame(tick) }
    }
    function stopRAF() {
      running = false; cancelAnimationFrame(rafId)
    }

    const onMouseMove = (e: MouseEvent) => { tx = e.clientX; ty = e.clientY }
    const onMouseEnter = () => { el.style.opacity = '1'; startRAF() }
    const onMouseLeave = () => { el.style.opacity = '0'; setTimeout(stopRAF, 400) }

    startRAF()
    el.style.opacity = '1'

    document.addEventListener('mousemove',  onMouseMove,  { passive: true })
    document.addEventListener('mouseleave', onMouseLeave, { passive: true })
    document.addEventListener('mouseenter', onMouseEnter, { passive: true })

    return () => {
      cancelAnimationFrame(rafId)
      document.removeEventListener('mousemove',  onMouseMove)
      document.removeEventListener('mouseleave', onMouseLeave)
      document.removeEventListener('mouseenter', onMouseEnter)
      if (el.parentNode) el.parentNode.removeChild(el)
    }
  }, [])
}

// ── Section scroll story — disabled: useScrollReveal() handles entrance
// animations cleanly via CSS transitions. GSAP ScrollTrigger on sections
// fights the [data-reveal] IntersectionObserver and causes invisible sections.

// ── Depth of Field — disabled: blur on non-focused sections degraded readability

// ── Card tilt — physical 3D response to cursor, no glow ─────────────────────
// [data-spotlight] cards respond with subtle tilt (±1.5°) and a shadow lift.
// Deferred via requestIdleCallback so it runs after hydration completes and
// all [data-spotlight] elements are in the DOM.
function useSpotlight() {
  useEffect(() => {
    if (!window.matchMedia('(pointer: fine)').matches) return
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return

    // Defer until idle so we don't run querySelectorAll before child components mount
    let idleId: number | undefined
    let timeoutId: ReturnType<typeof setTimeout> | undefined

    const setup = () => {
      const cards   = document.querySelectorAll<HTMLElement>('[data-spotlight]')
      const cleanup: Array<() => void> = []

      cards.forEach((card) => {
        card.querySelector('.spotlight-glow')?.remove()

        let pending = false
        let mx = 0, my = 0

        const applyFrame = () => {
          pending = false
          const rect = card.getBoundingClientRect()
          const x  = mx - rect.left
          const y  = my - rect.top
          const cx = rect.width  / 2
          const cy = rect.height / 2
          const dx = (x - cx) / cx
          const dy = (y - cy) / cy
          gsap.set(card, {
            rotateX: -dy * 1.5,
            rotateY:  dx * 1.5,
            transformPerspective: 1200,
          })
        }

        const onEnter = () => {
          gsap.to(card, {
            y: -5,
            boxShadow: '0 16px 48px rgba(0,0,0,0.11), 0 4px 12px rgba(0,0,0,0.06)',
            duration: 0.18,
            ease: 'power2.out',
            overwrite: 'auto',
          })
        }

        const onMove = (e: MouseEvent) => {
          mx = e.clientX; my = e.clientY
          if (!pending) { pending = true; requestAnimationFrame(applyFrame) }
        }

        const onLeave = () => {
          gsap.to(card, {
            y: 0,
            rotateX: 0,
            rotateY: 0,
            boxShadow: '0 4px 24px rgba(0,0,0,0.06)',
            duration: 0.6,
            ease: 'power3.out',
            overwrite: 'auto',
          })
        }

        card.addEventListener('mouseenter', onEnter, { passive: true })
        card.addEventListener('mousemove',  onMove,  { passive: true })
        card.addEventListener('mouseleave', onLeave, { passive: true })

        cleanup.push(() => {
          card.removeEventListener('mouseenter', onEnter)
          card.removeEventListener('mousemove',  onMove)
          card.removeEventListener('mouseleave', onLeave)
          gsap.set(card, { clearProps: 'y,rotateX,rotateY,transformPerspective,boxShadow' })
        })
      })

      return cleanup
    }

    let cleanupFns: Array<() => void> = []

    if (typeof requestIdleCallback !== 'undefined') {
      idleId = requestIdleCallback(() => { cleanupFns = setup() }, { timeout: 1500 })
    } else {
      timeoutId = setTimeout(() => { cleanupFns = setup() }, 400)
    }

    return () => {
      if (idleId !== undefined) cancelIdleCallback(idleId)
      if (timeoutId !== undefined) clearTimeout(timeoutId)
      cleanupFns.forEach(fn => fn())
    }
  }, [])
}

// ── Magnetic pull — physical cursor response, no glow ────────────────────────
// Deferred via requestIdleCallback so [data-magnetic] elements are in the DOM.
function useMagneticPull() {
  useEffect(() => {
    if (!window.matchMedia('(pointer: fine)').matches) return
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return

    let idleId: number | undefined
    let timeoutId: ReturnType<typeof setTimeout> | undefined

    const setup = () => {
      const targets = document.querySelectorAll<HTMLElement>('[data-magnetic]')
      const cleanup: Array<() => void> = []

      targets.forEach((el) => {
        el.querySelectorAll('[style*="radial-gradient"]').forEach(g => {
          if ((g as HTMLElement).style.pointerEvents === 'none') g.remove()
        })

        let rafId = 0

        const onMove = (e: MouseEvent) => {
          cancelAnimationFrame(rafId)
          rafId = requestAnimationFrame(() => {
            const rect = el.getBoundingClientRect()
            const cx = rect.left + rect.width  / 2
            const cy = rect.top  + rect.height / 2
            const dx = (e.clientX - cx) / (rect.width  / 2)
            const dy = (e.clientY - cy) / (rect.height / 2)
            gsap.to(el, {
              x: dx * 6,
              y: dy * 4,
              scale: 1.03,
              duration: 0.22,
              ease: 'power2.out',
              overwrite: 'auto',
            })
          })
        }

        const onLeave = () => {
          cancelAnimationFrame(rafId)
          gsap.to(el, {
            x: 0,
            y: 0,
            scale: 1,
            duration: 0.6,
            ease: 'elastic.out(1, 0.45)',
            overwrite: 'auto',
          })
        }

        el.addEventListener('mousemove',  onMove,  { passive: true })
        el.addEventListener('mouseleave', onLeave, { passive: true })

        cleanup.push(() => {
          cancelAnimationFrame(rafId)
          el.removeEventListener('mousemove',  onMove)
          el.removeEventListener('mouseleave', onLeave)
          gsap.set(el, { clearProps: 'x,y,scale' })
        })
      })

      return cleanup
    }

    let cleanupFns: Array<() => void> = []

    if (typeof requestIdleCallback !== 'undefined') {
      idleId = requestIdleCallback(() => { cleanupFns = setup() }, { timeout: 1500 })
    } else {
      timeoutId = setTimeout(() => { cleanupFns = setup() }, 400)
    }

    return () => {
      if (idleId !== undefined) cancelIdleCallback(idleId)
      if (timeoutId !== undefined) clearTimeout(timeoutId)
      cleanupFns.forEach(fn => fn())
    }
  }, [])
}

// ── Hero parallax — hero visualization responds gently to mouse movement ──────
// Targets the element with [data-hero-panel] — added to the RepoTree container
// in Hero.tsx. Extremely subtle ±8px shift that creates depth.
function useHeroParallax() {
  useEffect(() => {
    if (!window.matchMedia('(pointer: fine)').matches) return
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return

    // Use a stable data attribute — much safer than a deep CSS selector
    const heroPanel = document.querySelector<HTMLElement>('[data-hero-panel]')
    if (!heroPanel) return

    let rafId = 0
    let tx = 0, ty = 0, cx = 0, cy = 0

    const onMove = (e: MouseEvent) => {
      const nx = (e.clientX / window.innerWidth  - 0.5) * 2
      const ny = (e.clientY / window.innerHeight - 0.5) * 2
      tx = nx * 8
      ty = ny * 5
    }

    const tick = () => {
      cx += (tx - cx) * 0.06
      cy += (ty - cy) * 0.06
      gsap.set(heroPanel, { x: cx, y: cy, transformPerspective: 1200, overwrite: 'auto' })
      rafId = requestAnimationFrame(tick)
    }

    window.addEventListener('mousemove', onMove, { passive: true })
    rafId = requestAnimationFrame(tick)

    return () => {
      window.removeEventListener('mousemove', onMove)
      cancelAnimationFrame(rafId)
      gsap.set(heroPanel, { clearProps: 'x,y,transformPerspective' })
    }
  }, [])
}

export default function HomePage() {
  useLenis()
  useScrollReveal()
  useMouseSpotlight()
  useSpotlight()
  useMagneticPull()
  useHeroParallax()

  return (
    <div
      className="portfolio-page"
      style={{ fontFamily: "var(--font-sans,'DM Sans',system-ui,sans-serif)" }}
    >
      {/* ── Cyber-Aurora liquid blob background ── */}
      <div className="liquid-bg-mesh" aria-hidden="true">
        <div className="liquid-blob liquid-blob-1" />
        <div className="liquid-blob liquid-blob-2" />
        <div className="liquid-blob liquid-blob-3" />
      </div>

      <ScrollProgress />
      <PortfolioHeader />
      <main>
        <PortfolioHero />
        <PortfolioHowItWorks />
        <PortfolioSelectedWorks />
        <PortfolioAbout />
        <PortfolioClientLogos />
        <PortfolioTestimonials />
        <PortfolioAwards />
        <PortfolioInsights />
        <PortfolioFinalCTA />
      </main>
      <PortfolioFooter />
      <GradientBar />
    </div>
  )
}
