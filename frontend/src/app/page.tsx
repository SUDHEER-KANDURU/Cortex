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
import { MagneticCursor }         from "@/components/ui/magnetic-cursor"
import { ScrollProgress }         from "@/components/ui/scroll-progress"

const PortfolioHowItWorks = dynamic(
  () => import("@/components/landing/HowItWorks").then(m => ({ default: m.PortfolioHowItWorks })),
  {
    ssr: false,
    loading: () => (
      <div
        id="how-it-works"
        style={{
          height: "100vh",
          background: "rgba(255,255,255,0.72)",
          backdropFilter: "saturate(180%) blur(20px)",
          WebkitBackdropFilter: "saturate(180%) blur(20px)",
          borderTop: "1px solid rgba(255,255,255,0.9)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        {/* Lightweight skeleton — shows immediately while HowItWorks JS loads */}
        <div style={{ textAlign: "center" }}>
          <div style={{
            width: 180, height: 14, borderRadius: 7,
            background: "rgba(0,0,0,0.07)",
            animation: "pulse-skeleton 1.4s ease infinite",
            marginBottom: 12, marginLeft: "auto", marginRight: "auto",
          }} />
          <div style={{
            width: 120, height: 10, borderRadius: 5,
            background: "rgba(0,0,0,0.04)",
            animation: "pulse-skeleton 1.4s ease infinite 200ms",
            marginLeft: "auto", marginRight: "auto",
          }} />
        </div>
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
    lenis.on('scroll', () => ScrollTrigger.update())

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
      gsap.ticker.remove(tickerCallback)
      lenis.destroy()
    }
  }, [])
}

// ── Scroll-reveal (IntersectionObserver) ─────────────────────────────────────
function useScrollReveal() {
  useEffect(() => {
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
// The white glow overlay is intentionally removed — shadow creates depth
// without visual noise.
function useSpotlight() {
  useEffect(() => {
    if (!window.matchMedia('(pointer: fine)').matches) return
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return

    const cards   = document.querySelectorAll<HTMLElement>('[data-spotlight]')
    const cleanup: Array<() => void> = []

    cards.forEach((card) => {
      // Remove any previously injected glow overlays from old code
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
        const dx = (x - cx) / cx   // -1 … 1
        const dy = (y - cy) / cy   // -1 … 1

        // Tilt only — ±1.5° max, very restrained
        gsap.set(card, {
          rotateX: -dy * 1.5,
          rotateY:  dx * 1.5,
          transformPerspective: 1200,
        })
      }

      const onEnter = () => {
        // Lift with shadow — physical, no glow
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
        // Spring back — tilt, lift, shadow all return to rest
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

    return () => cleanup.forEach(fn => fn())
  }, [])
}

// ── Magnetic pull — physical cursor response, no glow ────────────────────────
// [data-magnetic] elements translate toward the cursor (max ±6px/4px) and
// scale very slightly. No color effects — movement and shadow only.
// Spring-back uses elastic ease for a physical, controlled feel.
function useMagneticPull() {
  useEffect(() => {
    if (!window.matchMedia('(pointer: fine)').matches) return
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return

    const targets = document.querySelectorAll<HTMLElement>('[data-magnetic]')
    const cleanup: Array<() => void> = []

    targets.forEach((el) => {
      // Remove any legacy glow overlays injected by previous code
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
          const dx = (e.clientX - cx) / (rect.width  / 2)  // -1 … 1
          const dy = (e.clientY - cy) / (rect.height / 2)  // -1 … 1

          // Restrained pull: 6px horizontal, 4px vertical max
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
        // Elastic spring-back — physical, not snappy
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

    return () => cleanup.forEach(fn => fn())
  }, [])
}

// ── Hero parallax — hero visualization responds gently to mouse movement ──────
// The dark panel in the hero shifts by ±8px as the cursor moves across the
// viewport. Extremely subtle — creates depth without distraction.
function useHeroParallax() {
  useEffect(() => {
    if (!window.matchMedia('(pointer: fine)').matches) return
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return

    // Target the hero dark panel — the RepoTree container
    // It's the first dark-background div inside the hero section
    const heroPanel = document.querySelector<HTMLElement>(
      '.portfolio-page main > div > div > div > div:last-child > div'
    )
    if (!heroPanel) return

    let rafId = 0
    let tx = 0, ty = 0, cx = 0, cy = 0

    const onMove = (e: MouseEvent) => {
      // Normalise to -1 … 1 across the viewport
      const nx = (e.clientX / window.innerWidth  - 0.5) * 2
      const ny = (e.clientY / window.innerHeight - 0.5) * 2
      // Target: max ±8px translate
      tx = nx * 8
      ty = ny * 5
    }

    const tick = () => {
      cx += (tx - cx) * 0.06  // slow lerp — lazy, dreamy
      cy += (ty - cy) * 0.06
      gsap.set(heroPanel, {
        x: cx,
        y: cy,
        transformPerspective: 1200,
        overwrite: 'auto',
      })
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
      <ScrollProgress />
      <MagneticCursor />
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
