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
  { ssr: false, loading: () => <div style={{ height: "120px" }} /> },
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

// ── Mouse spotlight — radial gradient that follows cursor on pointer:fine devices ──
// Creates a single fixed div on document.body with a 280px radial gradient.
// Position is lerped at 0.08 per RAF frame for a smooth lag effect.
// Opacity fades to 0 on mouseleave and resumes on mouseenter.
// Only attaches on devices where pointer:fine (mouse/trackpad, not touch/stylus).
function useMouseSpotlight() {
  useEffect(() => {
    // Guard: only attach on fine-pointer (mouse/trackpad) devices
    if (!window.matchMedia('(pointer: fine)').matches) return

    // Create the spotlight overlay element
    const el = document.createElement('div')
    el.setAttribute('data-mouse-spotlight', '')
    el.style.cssText = [
      'position:fixed',
      'inset:0',
      'pointer-events:none',
      'z-index:0',
      // gradient position driven by CSS custom props to avoid re-parsing on every frame
      'background:radial-gradient(280px circle at var(--sx,50%) var(--sy,50%),rgba(255,255,255,0.07) 0%,transparent 70%)',
      'opacity:0',
      'transition:opacity 300ms ease',
    ].join(';')
    document.body.insertBefore(el, document.body.firstChild)

    // Lerp state — current (cx/cy) and target (tx/ty) positions
    let cx = 0, cy = 0, tx = 0, ty = 0
    let rafId: number
    let running = false

    function tick() {
      cx += (tx - cx) * 0.08
      cy += (ty - cy) * 0.08
      el.style.setProperty('--sx', `${cx}px`)
      el.style.setProperty('--sy', `${cy}px`)
      rafId = requestAnimationFrame(tick)
    }

    function startRAF() {
      if (!running) {
        running = true
        rafId = requestAnimationFrame(tick)
      }
    }

    function stopRAF() {
      running = false
      cancelAnimationFrame(rafId)
    }

    const onMouseMove = (e: MouseEvent) => {
      tx = e.clientX
      ty = e.clientY
    }

    const onMouseEnter = () => {
      el.style.opacity = '1'
      startRAF()
    }

    const onMouseLeave = () => {
      // Fade to invisible; stop the RAF loop after the transition to save CPU
      el.style.opacity = '0'
      // Stop RAF after the 300ms fade completes
      setTimeout(stopRAF, 300)
    }

    // Start running immediately (cursor may already be in the window)
    startRAF()
    el.style.opacity = '1'

    document.addEventListener('mousemove',  onMouseMove,  { passive: true })
    document.addEventListener('mouseleave', onMouseLeave, { passive: true })
    document.addEventListener('mouseenter', onMouseEnter, { passive: true })

    return () => {
      // Cancel RAF and remove DOM element on unmount
      cancelAnimationFrame(rafId)
      document.removeEventListener('mousemove',  onMouseMove)
      document.removeEventListener('mouseleave', onMouseLeave)
      document.removeEventListener('mouseenter', onMouseEnter)
      if (el.parentNode) el.parentNode.removeChild(el)
    }
  }, [])
}

// ── Section scroll story — entrance + exit animations via GSAP ScrollTrigger ─
// Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 9.6
//
// Attaches two ScrollTrigger-driven tweens to every <section> inside <main>:
//   • Entrance: opacity 0 + y 48 → opacity 1 + y 0 over 0.9s (cubic.out)
//   • Exit    : opacity 1 + y 0 → opacity 0.6 + y -24 over 0.6s (cubic.out)
//              onReverseComplete resets to full opacity / no transform
//
// Skips the fixed <header> (not inside <main>) and the Hero / HowItWorks
// containers (those are <div>s with their own timelines, not <section>s).
//
// CLS prevention: every targeted <section> is given an explicit min-height
// equal to its natural offsetHeight before any GSAP inline style is applied,
// so the layout cannot shift when opacity/transform are set.
//
// prefers-reduced-motion: early-returns before creating any ScrollTrigger.
// All ScrollTrigger instances are killed on unmount to prevent memory leaks.
function useScrollStory() {
  useEffect(() => {
    // Req 5.6 — if visitor prefers reduced motion, skip entirely
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return

    // Target only <section> landmarks inside <main>.
    // This naturally excludes:
    //   - <header> (PortfolioHeader is fixed, outside <main>)
    //   - Hero container (a <div>, not a <section>)
    //   - HowItWorks container (a <div> with its own GSAP timeline)
    const sections = Array.from(
      document.querySelectorAll<HTMLElement>('main section')
    )

    if (sections.length === 0) return

    const triggers: ReturnType<typeof ScrollTrigger.create>[] = []

    sections.forEach((section) => {
      // Req 5.7 / CLS prevention — lock the section's natural height before
      // GSAP sets inline opacity/transform so the document layout stays stable.
      if (!section.style.minHeight) {
        const naturalHeight = section.offsetHeight
        if (naturalHeight > 0) {
          section.style.minHeight = `${naturalHeight}px`
        }
      }

      // ── Entrance animation ─────────────────────────────────────────────────
      // From opacity:0, y:48 → opacity:1, y:0 over 0.9s when section enters
      // the viewport from below.
      const entranceTrigger = ScrollTrigger.create({
        trigger: section,
        start: 'top 88%',     // section top crosses 88% from viewport top
        end: 'top 20%',       // don't re-trigger once well inside view
        onEnter: () => {
          gsap.fromTo(
            section,
            { opacity: 0, y: 48 },
            {
              opacity: 1,
              y: 0,
              duration: 0.9,
              ease: 'cubic.out',
              overwrite: 'auto',
            }
          )
        },
        onLeaveBack: () => {
          // Reset when scrolling back up past trigger so it can re-entrance
          gsap.set(section, { opacity: 0, y: 48 })
        },
      })

      // ── Exit animation ─────────────────────────────────────────────────────
      // When section scrolls upward and exits the viewport top, fade to 0.6
      // and shift up -24px (the "already read" state). On reverse (scroll
      // back down into it), snap back to full opacity / no transform.
      const exitTrigger = ScrollTrigger.create({
        trigger: section,
        start: 'top top',      // section top hits viewport top
        end: 'bottom top',     // section has fully passed out of view
        onLeave: () => {
          // Section has scrolled completely above the viewport
          gsap.to(section, {
            opacity: 0.6,
            y: -24,
            duration: 0.6,
            ease: 'cubic.out',
            overwrite: 'auto',
          })
        },
        onEnterBack: () => {
          // Scrolling back down — section re-enters from the top: restore
          gsap.to(section, {
            opacity: 1,
            y: 0,
            duration: 0.6,
            ease: 'cubic.out',
            overwrite: 'auto',
          })
        },
      })

      triggers.push(entranceTrigger, exitTrigger)
    })

    // Req 9.6 — kill every instance on unmount to prevent memory leaks
    return () => {
      triggers.forEach((t) => t.kill())
    }
  }, [])
}

// ── Depth of Field — blur/focus CSS class toggle via ScrollTrigger ───────────
// Requirements 12.1, 12.2, 12.3, 12.4, 12.5, 12.6
//
// Attaches one ScrollTrigger per <section> inside <main>. When a section
// occupies >50% of the viewport it receives `.section-dof-focus` (blur: 0px).
// All sections that are fully outside the viewport receive `.section-dof-blur`
// (blur: 2px — capped by the CSS class itself).
//
// Skips the fixed <header> (not inside <main> and position:fixed) and any
// element with a computed `position: fixed` style.
//
// prefers-reduced-motion: hook early-returns so no classes are ever applied
// and all sections remain at blur(0px) (CSS media query also enforces this).
//
// All ScrollTrigger instances are killed on unmount to prevent memory leaks.
function useDepthOfField() {
  useEffect(() => {
    // Req 12.5 — if reduced motion, skip class toggling entirely
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return

    // Target only <section> landmarks inside <main>.
    // This naturally excludes <header> (PortfolioHeader is fixed, outside <main>).
    const allSections = Array.from(
      document.querySelectorAll<HTMLElement>('main section')
    )

    // Req 12.4 — additionally filter out any position:fixed elements
    const sections = allSections.filter((el) => {
      const style = window.getComputedStyle(el)
      return style.position !== 'fixed'
    })

    if (sections.length === 0) return

    const triggers: ReturnType<typeof ScrollTrigger.create>[] = []

    sections.forEach((section) => {
      // When a section enters focus (occupies >50% of viewport height):
      //   - add .section-dof-focus, remove .section-dof-blur on THIS section
      //   - add .section-dof-blur, remove .section-dof-focus on ALL OTHER sections
      //     that are fully outside the viewport
      //
      // The trigger fires when the section's visible portion crosses the 50%
      // viewport coverage threshold:
      //   • start: 'top 50%' — top edge of section crosses midpoint → entering focus
      //   • end:   'bottom 50%' — bottom edge of section crosses midpoint → leaving focus
      const trigger = ScrollTrigger.create({
        trigger: section,
        start: 'top 50%',
        end: 'bottom 50%',

        onEnter() {
          // This section is now in focus
          section.classList.add('section-dof-focus')
          section.classList.remove('section-dof-blur')

          // Blur all other sections that are fully outside the viewport
          sections.forEach((other) => {
            if (other === section) return
            const rect = other.getBoundingClientRect()
            const isFullyOutside = rect.bottom < 0 || rect.top > window.innerHeight
            if (isFullyOutside) {
              other.classList.add('section-dof-blur')
              other.classList.remove('section-dof-focus')
            }
          })
        },

        onLeave() {
          // Section has scrolled above viewport midpoint — it's no longer in focus
          section.classList.remove('section-dof-focus')
          // It's now above the viewport, so blur it
          section.classList.add('section-dof-blur')
        },

        onEnterBack() {
          // Scrolling back down — this section re-enters focus from above
          section.classList.add('section-dof-focus')
          section.classList.remove('section-dof-blur')

          // Blur sections that are fully outside the viewport
          sections.forEach((other) => {
            if (other === section) return
            const rect = other.getBoundingClientRect()
            const isFullyOutside = rect.bottom < 0 || rect.top > window.innerHeight
            if (isFullyOutside) {
              other.classList.add('section-dof-blur')
              other.classList.remove('section-dof-focus')
            }
          })
        },

        onLeaveBack() {
          // Section has scrolled below the viewport midpoint (not yet in focus)
          section.classList.remove('section-dof-focus')
          // It's below the viewport, so blur it
          section.classList.add('section-dof-blur')
        },
      })

      triggers.push(trigger)
    })

    // Req 9.6 — kill every instance on unmount to prevent memory leaks
    return () => {
      triggers.forEach((t) => t.kill())
      // Clean up classes to leave elements in a neutral state
      sections.forEach((section) => {
        section.classList.remove('section-dof-blur', 'section-dof-focus')
      })
    }
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

        // Tilt — max ±3deg, very subtle (GSAP controls y; we only set rotateX/Y here)
        const cx = rect.width  / 2
        const cy = rect.height / 2
        const dx = (x - cx) / cx
        const dy = (y - cy) / cy
        gsap.set(card, {
          rotateX: (-dy * 2.5),
          rotateY: (dx * 2.5),
          transformPerspective: 1000,
        })
      }

      const onEnter = () => {
        // Physics_Hover lift — quick snap up
        gsap.to(card, { y: -6, duration: 0.1, ease: 'power2.out' })
      }

      const onMove = (e: MouseEvent) => {
        mx = e.clientX; my = e.clientY
        if (!pending) {
          pending = true
          requestAnimationFrame(applyFrame)
        }
      }

      const onLeave = () => {
        glow.style.opacity = '0'
        // Spring-back: y, rotateX, rotateY all return to rest
        gsap.to(card, {
          y: 0,
          rotateX: 0,
          rotateY: 0,
          duration: 0.55,
          ease: 'power2.out',
        })
      }

      card.addEventListener('mouseenter', onEnter,  { passive: true })
      card.addEventListener('mousemove',  onMove,   { passive: true })
      card.addEventListener('mouseleave', onLeave,  { passive: true })
      cleanup.push(() => {
        card.removeEventListener('mouseenter', onEnter)
        card.removeEventListener('mousemove',  onMove)
        card.removeEventListener('mouseleave', onLeave)
        gsap.set(card, { clearProps: 'y,rotateX,rotateY,transformPerspective' })
      })
    })

    return () => cleanup.forEach(fn => fn())
  }, [])
}

// ── Magnetic pull — buttons and nav links get pulled toward cursor + scale up ─
// On mouseenter the element translates toward the cursor (max ±8px) and scales
// to 1.06. On mouseleave it springs back with elastic ease.
// Dark buttons ([data-magnetic-dark]) also get an orange radial glow under the cursor.
// Applied to: [data-magnetic] elements (buttons, CTAs, nav items).
function useMagneticPull() {
  useEffect(() => {
    if (!window.matchMedia('(pointer: fine)').matches) return
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return

    const targets = document.querySelectorAll<HTMLElement>('[data-magnetic]')
    const cleanup: Array<() => void> = []

    targets.forEach((el) => {
      let rafId = 0
      // Inject glow overlay for dark buttons
      const isDark = el.hasAttribute('data-magnetic-dark') ||
        el.style.background?.includes('#0a0a0a') ||
        el.style.background?.includes('#111') ||
        el.style.background?.includes('#000') ||
        getComputedStyle(el).backgroundColor === 'rgb(10, 10, 10)' ||
        getComputedStyle(el).backgroundColor === 'rgb(17, 17, 17)'

      let glowEl: HTMLDivElement | null = null
      if (isDark) {
        glowEl = document.createElement('div')
        glowEl.style.cssText = [
          'position:absolute',
          'inset:0',
          'border-radius:inherit',
          'pointer-events:none',
          'z-index:1',
          'opacity:0',
          'transition:opacity 0.25s ease',
          'background:radial-gradient(60% 100% at var(--gx,50%) var(--gy,50%), rgba(255,140,0,0.45) 0%, rgba(255,100,0,0.18) 45%, transparent 80%)',
          'mix-blend-mode:screen',
        ].join(';')
        const pos = getComputedStyle(el).position
        if (pos === 'static') el.style.position = 'relative'
        el.style.overflow = 'hidden'
        el.appendChild(glowEl)
      }

      const onMove = (e: MouseEvent) => {
        cancelAnimationFrame(rafId)
        rafId = requestAnimationFrame(() => {
          const rect = el.getBoundingClientRect()
          const cx = rect.left + rect.width  / 2
          const cy = rect.top  + rect.height / 2
          // Normalised offset from center (-1 … 1)
          const dx = (e.clientX - cx) / (rect.width  / 2)
          const dy = (e.clientY - cy) / (rect.height / 2)

          // Update glow position
          if (glowEl) {
            const gx = ((e.clientX - rect.left) / rect.width)  * 100
            const gy = ((e.clientY - rect.top)  / rect.height) * 100
            glowEl.style.setProperty('--gx', `${gx}%`)
            glowEl.style.setProperty('--gy', `${gy}%`)
            glowEl.style.opacity = '1'
          }

          // Pull strength: max 8px horizontal, 5px vertical
          gsap.to(el, {
            x: dx * 8,
            y: dy * 5,
            scale: isDark ? 1.08 : 1.05,
            duration: 0.2,
            ease: 'power2.out',
            overwrite: 'auto',
          })
        })
      }

      const onEnter = () => {
        if (glowEl) glowEl.style.opacity = '0.85'
      }

      const onLeave = () => {
        cancelAnimationFrame(rafId)
        if (glowEl) glowEl.style.opacity = '0'
        gsap.to(el, {
          x: 0,
          y: 0,
          scale: 1,
          duration: 0.55,
          ease: 'elastic.out(1, 0.4)',
          overwrite: 'auto',
        })
      }

      el.addEventListener('mouseenter', onEnter,  { passive: true })
      el.addEventListener('mousemove',  onMove,   { passive: true })
      el.addEventListener('mouseleave', onLeave,  { passive: true })
      cleanup.push(() => {
        cancelAnimationFrame(rafId)
        el.removeEventListener('mouseenter', onEnter)
        el.removeEventListener('mousemove',  onMove)
        el.removeEventListener('mouseleave', onLeave)
        if (glowEl && glowEl.parentNode) glowEl.parentNode.removeChild(glowEl)
        gsap.set(el, { clearProps: 'x,y,scale' })
      })
    })

    return () => cleanup.forEach(fn => fn())
  }, [])
}

export default function HomePage() {
  useLenis()
  useScrollReveal()
  useMouseSpotlight()
  // useScrollStory() — disabled: GSAP entrance/exit on sections fights the
  // [data-reveal] IntersectionObserver system, causing sections to render
  // invisible (opacity:0) before their trigger fires. useScrollReveal() handles
  // entrance animations cleanly via CSS transitions — no GSAP needed.
  // useDepthOfField() — disabled: blur on non-focused sections degraded readability
  useSpotlight()
  useMagneticPull()

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
