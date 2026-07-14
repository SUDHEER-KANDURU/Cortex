'use client'

import { useEffect, useLayoutEffect } from 'react'
import dynamic from 'next/dynamic'
import Lenis from 'lenis'
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
  { ssr: false, loading: () => <div style={{ height: "120px" }} /> },
)

// ── Lenis smooth scroll — Apple-tuned ────────────────────────────────────────
// duration 0.9 = fast, precise like Safari native scroll
// easing = ease-out exponential (same curve Apple uses on iOS momentum)
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

    let rafId: number
    function raf(time: number) {
      lenis.raf(time)
      rafId = requestAnimationFrame(raf)
    }
    rafId = requestAnimationFrame(raf)

    return () => {
      cancelAnimationFrame(rafId)
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

// ── Spotlight + 3D tilt — RAF-throttled for 60fps ────────────────────────────
// Raw mousemove fires at 200+fps; we throttle to rAF (~60fps) to prevent jank
function useSpotlight() {
  useEffect(() => {
    const cards   = document.querySelectorAll<HTMLElement>('[data-spotlight]')
    const cleanup: Array<() => void> = []

    cards.forEach((card) => {
      // Inject glow overlay once
      if (!card.querySelector('.spotlight-glow')) {
        const g = document.createElement('div')
        g.className  = 'spotlight-glow'
        g.style.cssText = [
          'position:absolute', 'inset:0', 'border-radius:inherit',
          'pointer-events:none', 'z-index:1', 'opacity:0',
          'transition:opacity 0.4s ease',
        ].join(';')
        card.style.position = card.style.position || 'relative'
        card.insertBefore(g, card.firstChild)
      }

      const glow = card.querySelector<HTMLElement>('.spotlight-glow')!
      let pending = false
      let mx = 0, my = 0

      const applyFrame = () => {
        pending = false
        const rect = card.getBoundingClientRect()
        const x = mx - rect.left
        const y = my - rect.top

        // Spotlight
        glow.style.background = `radial-gradient(260px circle at ${x}px ${y}px, rgba(255,255,255,0.13), transparent 65%)`
        glow.style.opacity = '1'

        // Tilt — max ±3deg, very subtle
        const cx = rect.width  / 2
        const cy = rect.height / 2
        const dx = (x - cx) / cx
        const dy = (y - cy) / cy
        card.style.transform  = `perspective(1000px) rotateX(${(-dy * 2.5).toFixed(2)}deg) rotateY(${(dx * 2.5).toFixed(2)}deg) translateZ(0)`
        card.style.transition = 'transform 0.08s linear'
      }

      const onMove = (e: MouseEvent) => {
        mx = e.clientX; my = e.clientY
        if (!pending) {
          pending = true
          requestAnimationFrame(applyFrame)
        }
      }

      const onLeave = () => {
        glow.style.opacity   = '0'
        card.style.transform = 'perspective(1000px) rotateX(0deg) rotateY(0deg) translateZ(0)'
        card.style.transition = 'transform 0.55s cubic-bezier(0.16,1,0.3,1)'
      }

      card.addEventListener('mousemove',  onMove,  { passive: true })
      card.addEventListener('mouseleave', onLeave, { passive: true })
      cleanup.push(() => {
        card.removeEventListener('mousemove',  onMove)
        card.removeEventListener('mouseleave', onLeave)
        card.style.transform = ''
      })
    })

    return () => cleanup.forEach(fn => fn())
  }, [])
}

export default function HomePage() {
  useLenis()
  useScrollReveal()
  useSpotlight()

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
