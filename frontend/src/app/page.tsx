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

// ── Hero parallax — hero visualization responds gently to mouse movement ──────
// Targets the element with [data-hero-panel] — added to the RepoTree container
// in Hero.tsx. Extremely subtle ±8px shift that creates depth.
// The RAF loop is paused automatically when the hero panel scrolls off-screen
// using an IntersectionObserver, saving ~60 GSAP calls/s during the rest of
// the landing page scroll.
function useHeroParallax() {
  useEffect(() => {
    if (!window.matchMedia('(pointer: fine)').matches) return
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return

    const heroPanel = document.querySelector<HTMLElement>('[data-hero-panel]')
    if (!heroPanel) return

    let rafId = 0
    let tx = 0, ty = 0, cx = 0, cy = 0
    let isVisible = true

    const onMove = (e: MouseEvent) => {
      const nx = (e.clientX / window.innerWidth  - 0.5) * 2
      const ny = (e.clientY / window.innerHeight - 0.5) * 2
      tx = nx * 8
      ty = ny * 5
    }

    const tick = () => {
      if (isVisible) {
        const dx = tx - cx
        const dy = ty - cy
        // Skip GSAP call when lerp has settled (delta < 0.05px)
        if (Math.abs(dx) > 0.05 || Math.abs(dy) > 0.05) {
          cx += dx * 0.06
          cy += dy * 0.06
          gsap.set(heroPanel, { x: cx, y: cy, transformPerspective: 1200, overwrite: 'auto' })
        }
      }
      rafId = requestAnimationFrame(tick)
    }

    // Pause when hero is fully off-screen — no point animating invisible element
    const io = new IntersectionObserver(
      ([entry]) => { isVisible = entry.isIntersecting },
      { threshold: 0 },
    )
    io.observe(heroPanel)

    window.addEventListener('mousemove', onMove, { passive: true })
    rafId = requestAnimationFrame(tick)

    return () => {
      window.removeEventListener('mousemove', onMove)
      cancelAnimationFrame(rafId)
      io.disconnect()
      gsap.set(heroPanel, { clearProps: 'x,y,transformPerspective' })
    }
  }, [])
}

export default function HomePage() {
  useLenis()
  useScrollReveal()
  useSpotlight()
  useHeroParallax()

  return (
    <div
      className="portfolio-page"
      style={{ fontFamily: "var(--font-sans,'Inter',system-ui,sans-serif)" }}
    >
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

