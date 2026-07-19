"use client"

import type React from "react"
import { useState, useEffect, useRef, useCallback } from "react"
import Link from "next/link"
import { X, LayoutDashboard } from "lucide-react"

// =============================================================================
// PortfolioHeader — Liquid Glass navbar with continuous scroll interpolation
//
// Scroll transition strategy
// ──────────────────────────
// Instead of a boolean `scrolled` state that snaps between two style sets,
// we track a progress value p ∈ [0, 1] that sweeps from 0 to 1 as the page
// scrolls from 0px to SCROLL_RANGE px (60px).
//
// Every property is linearly interpolated between its "at-top" and "scrolled"
// endpoints using that progress value. The lerp runs inside a rAF loop that
// writes directly to CSS custom properties on the nav DOM node — no React
// re-renders, no CSS transition delays, no jank.
//
// Spring easing is applied by smoothing p itself: on each tick we lerp the
// displayed progress toward the target with a factor of 0.10 (~100ms settle).
// This gives the "spring-like" feel without any animation library.
// =============================================================================

const SCROLL_RANGE = 60  // px over which the full transition occurs

// ── Interpolation helper ──────────────────────────────────────────────────────
const lerp = (a: number, b: number, t: number) => a + (b - a) * t

// ── Section IDs ───────────────────────────────────────────────────────────────
const navItems = [
  { href: "#works",        label: "Capabilities", id: "works"        },
  { href: "#about",        label: "About",         id: "about"        },
  { href: "#testimonials", label: "Artifacts",     id: "testimonials" },
  { href: "#awards",       label: "Stack",          id: "awards"       },
  { href: "#insights",     label: "Insights",       id: "insights"     },
]

export function PortfolioHeader() {
  const [isMobileMenuOpen, setMobileOpen] = useState(false)
  const [activeSection, setActiveSection] = useState<string>("")

  // Direct DOM refs — bypasses React render cycle for the scroll animation
  const navRef     = useRef<HTMLElement>(null)
  const headerRef  = useRef<HTMLElement>(null)

  // Scroll progress state — lives outside React
  const targetP = useRef(0)   // raw 0-1 from scroll position
  const currentP = useRef(0)  // smoothed 0-1 (spring lerp)
  const rafId    = useRef<number | null>(null)

  // ── Apply interpolated styles directly to DOM ─────────────────────────────
  // Called every rAF tick. All values are lerped between at-top and scrolled.
  const applyStyles = useCallback((p: number) => {
    const nav = navRef.current
    const hdr = headerRef.current
    if (!nav || !hdr) return

    // Header top padding: 10px → 6px
    hdr.style.paddingTop = `${lerp(10, 6, p)}px`

    // Background opacity: 0.72 → 0.92
    const bgAlpha = lerp(0.72, 0.92, p)
    nav.style.background = `rgba(255,255,255,${bgAlpha.toFixed(3)})`

    // Backdrop blur: 20px → 28px (written as filter string)
    const blurPx  = lerp(20, 28, p)
    const satPct  = lerp(180, 200, p)
    nav.style.backdropFilter = `saturate(${satPct.toFixed(0)}%) blur(${blurPx.toFixed(1)}px)`;
    (nav.style as unknown as Record<string, string>)["-webkit-backdrop-filter"] = `saturate(${satPct.toFixed(0)}%) blur(${blurPx.toFixed(1)}px)`

    // Top border (bright highlight): opacity 0.82 → 0.96
    const topBorderAlpha = lerp(0.82, 0.96, p)
    nav.style.borderTop   = `1px solid rgba(255,255,255,${topBorderAlpha.toFixed(3)})`

    // Bottom border (depth): opacity 0.03 → 0.08
    const btmBorderAlpha = lerp(0.03, 0.08, p)
    nav.style.borderBottom = `1px solid rgba(0,0,0,${btmBorderAlpha.toFixed(3)})`

    // Left + right border: same as top
    nav.style.borderLeft  = `1px solid rgba(255,255,255,${topBorderAlpha.toFixed(3)})`
    nav.style.borderRight = `1px solid rgba(255,255,255,${topBorderAlpha.toFixed(3)})`

    // Shadow — interpolate between two composited shadow stacks
    // At top: 1 layer, soft. Scrolled: 4 layers, structured.
    const s1Blur  = lerp(8,  32, p)   // outer diffuse
    const s1Alpha = lerp(0.05, 0.10, p)
    const s2Blur  = lerp(0,   6, p)   // tight shadow
    const s2Alpha = lerp(0,   0.06, p)
    const inTop   = lerp(0.90, 1.0, p) // inner top highlight (as 255*alpha)
    const inBtm   = lerp(0.02, 0.04, p) // inner bottom depth
    nav.style.boxShadow = [
      `0 ${lerp(1, 8, p).toFixed(1)}px ${s1Blur.toFixed(0)}px rgba(0,0,0,${s1Alpha.toFixed(3)})`,
      p > 0.05 ? `0 1px ${s2Blur.toFixed(0)}px rgba(0,0,0,${s2Alpha.toFixed(3)})` : "",
      `inset 0 1px 0 rgba(255,255,255,${inTop.toFixed(3)})`,
      `inset 0 -1px 0 rgba(0,0,0,${inBtm.toFixed(3)})`,
    ].filter(Boolean).join(", ")
  }, [])

  // ── rAF loop ──────────────────────────────────────────────────────────────
  const tick = useCallback(() => {
    // Spring toward target: factor 0.10 gives ~100ms settle at 60fps
    const prev = currentP.current
    const next = prev + (targetP.current - prev) * 0.10

    // Only update DOM when value has meaningfully changed (avoid wasteful writes)
    if (Math.abs(next - prev) > 0.0005) {
      currentP.current = next
      applyStyles(next)
    }

    rafId.current = requestAnimationFrame(tick)
  }, [applyStyles])

  // ── Scroll listener + section observers ──────────────────────────────────
  useEffect(() => {
    // Apply initial styles immediately (no flash)
    applyStyles(0)

    const onScroll = () => {
      targetP.current = Math.min(window.scrollY / SCROLL_RANGE, 1)
    }
    onScroll()

    window.addEventListener("scroll", onScroll, { passive: true })
    rafId.current = requestAnimationFrame(tick)

    // Section active-state via IntersectionObserver
    const observers: IntersectionObserver[] = []
    navItems.forEach(({ id }) => {
      const el = document.getElementById(id)
      if (!el) return
      const obs = new IntersectionObserver(
        ([entry]) => { if (entry.isIntersecting) setActiveSection(id) },
        { threshold: 0.15, rootMargin: "-72px 0px -40% 0px" },
      )
      obs.observe(el)
      observers.push(obs)
    })

    return () => {
      window.removeEventListener("scroll", onScroll)
      if (rafId.current !== null) cancelAnimationFrame(rafId.current)
      observers.forEach(o => o.disconnect())
    }
  }, [tick, applyStyles])

  // ── Smooth scroll on nav click ────────────────────────────────────────────
  const handleNavClick = (
    e: React.MouseEvent<HTMLAnchorElement>,
    href: string,
    id: string,
  ) => {
    e.preventDefault()
    setActiveSection(id)
    const el = document.querySelector(href)
    if (el) {
      const top = el.getBoundingClientRect().top + window.pageYOffset - 72
      window.scrollTo({ top, behavior: "smooth" })
    }
    setMobileOpen(false)
  }

  // ── Fixed inner styles (not scroll-dependent) ─────────────────────────────
  const navBaseStyle: React.CSSProperties = {
    pointerEvents: "auto",
    // background, backdropFilter, border, boxShadow all managed by rAF above
    borderRadius: "100px",
    padding: "4px 4px 4px 6px",
    display: "flex",
    alignItems: "center",
    gap: "2px",
    // No CSS transition — rAF interpolation is the animation
  }

  return (
    <>
      {/* ── Header ────────────────────────────────────────────────────────── */}
      <header
        ref={headerRef}
        className="fixed top-0 left-0 right-0 z-[200] flex justify-center"
        style={{ pointerEvents: "none", paddingTop: "10px" }}
      >
        <nav
          ref={navRef}
          aria-label="Main navigation"
          style={navBaseStyle}
        >
          {/* ── Logo ──────────────────────────────────────────────────── */}
          <Link
            href="#"
            onClick={e => {
              e.preventDefault()
              setActiveSection("")
              window.scrollTo({ top: 0, behavior: "smooth" })
            }}
            aria-label="Cortex — back to top"
            style={{
              display: "flex", alignItems: "center", gap: "7px",
              padding: "6px 14px 6px 7px",
              borderRadius: "100px",
              textDecoration: "none",
              transition: "background 0.2s ease",
            }}
            onMouseEnter={e => (e.currentTarget.style.background = "rgba(0,0,0,0.045)")}
            onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
          >
            <span style={{
              width: 26, height: 26, borderRadius: "8px",
              background: "#0a0a0a",
              display: "inline-flex", alignItems: "center", justifyContent: "center",
              flexShrink: 0,
              boxShadow: [
                "0 1px 4px rgba(0,0,0,0.35)",
                "inset 0 1px 0 rgba(255,255,255,0.12)",
                "inset 0 -1px 0 rgba(0,0,0,0.2)",
              ].join(", "),
            }}>
              <LayoutDashboard style={{ width: 12, height: 12, color: "#fff" }} />
            </span>
            <span style={{
              fontFamily: "var(--font-display,'Syne',sans-serif)",
              fontSize: "14px", fontWeight: 700,
              letterSpacing: "-0.03em", color: "#0a0a0a",
            }}>
              Cortex
            </span>
          </Link>

          {/* ── Desktop nav links ──────────────────────────────────────── */}
          <div className="hidden md:flex items-center gap-0.5" role="list">
            {navItems.map(({ href, label, id }) => {
              const isActive = activeSection === id
              return (
                <Link
                  key={href}
                  href={href}
                  role="listitem"
                  onClick={e => handleNavClick(e, href, id)}
                  style={{
                    display: "flex", alignItems: "center",
                    padding: "6px 12px",
                    borderRadius: "100px",
                    fontSize: "13px",
                    fontWeight: isActive ? 600 : 450,
                    background: isActive ? "rgba(0,0,0,0.08)" : "transparent",
                    color: isActive ? "rgba(0,0,0,0.85)" : "rgba(0,0,0,0.42)",
                    textDecoration: "none",
                    letterSpacing: isActive ? "-0.01em" : "0",
                    whiteSpace: "nowrap",
                    fontFamily: "var(--font-sans,'DM Sans',sans-serif)",
                    transition: "background 0.22s ease, color 0.22s ease",
                  }}
                  onMouseEnter={e => {
                    if (!isActive) {
                      e.currentTarget.style.background = "rgba(0,0,0,0.05)"
                      e.currentTarget.style.color = "rgba(0,0,0,0.65)"
                    }
                  }}
                  onMouseLeave={e => {
                    if (!isActive) {
                      e.currentTarget.style.background = "transparent"
                      e.currentTarget.style.color = "rgba(0,0,0,0.42)"
                    }
                  }}
                >
                  {label}
                  {isActive && (
                    <span style={{
                      display: "inline-block",
                      width: 3, height: 3, borderRadius: "50%",
                      background: "rgba(0,0,0,0.5)",
                      marginLeft: 6, flexShrink: 0,
                    }} />
                  )}
                </Link>
              )
            })}
          </div>

          {/* ── CTA ────────────────────────────────────────────────────── */}
          <Link
            href="/dashboard"
            className="hidden md:inline-flex items-center justify-center"
            style={{
              marginLeft: "6px",
              padding: "7px 16px",
              borderRadius: "100px",
              background: "#0a0a0a",
              color: "#fff",
              fontSize: "13px",
              fontWeight: 600,
              textDecoration: "none",
              letterSpacing: "-0.01em",
              boxShadow: [
                "0 1px 6px rgba(0,0,0,0.24)",
                "0 0 0 1px rgba(255,255,255,0.06)",
                "inset 0 1px 0 rgba(255,255,255,0.10)",
                "inset 0 -1px 0 rgba(0,0,0,0.2)",
              ].join(", "),
              whiteSpace: "nowrap",
              fontFamily: "var(--font-sans,'DM Sans',sans-serif)",
              transition: "box-shadow 0.22s ease, background 0.18s ease",
            }}
            onMouseEnter={e => {
              e.currentTarget.style.background = "#111"
              e.currentTarget.style.boxShadow = [
                "0 3px 14px rgba(0,0,0,0.32)",
                "0 0 0 1px rgba(255,255,255,0.08)",
                "inset 0 1px 0 rgba(255,255,255,0.12)",
                "inset 0 -1px 0 rgba(0,0,0,0.2)",
              ].join(", ")
            }}
            onMouseLeave={e => {
              e.currentTarget.style.background = "#0a0a0a"
              e.currentTarget.style.boxShadow = [
                "0 1px 6px rgba(0,0,0,0.24)",
                "0 0 0 1px rgba(255,255,255,0.06)",
                "inset 0 1px 0 rgba(255,255,255,0.10)",
                "inset 0 -1px 0 rgba(0,0,0,0.2)",
              ].join(", ")
            }}
          >
            Launch App
          </Link>

          {/* ── Mobile burger ──────────────────────────────────────────── */}
          <button
            onClick={() => setMobileOpen(true)}
            className="md:hidden flex items-center justify-center"
            aria-label="Open navigation menu"
            style={{
              marginLeft: "4px",
              width: 36, height: 36, borderRadius: "100px",
              background: "rgba(0,0,0,0.05)",
              border: "1px solid rgba(0,0,0,0.08)",
              cursor: "pointer", color: "#0a0a0a", flexShrink: 0,
              transition: "background 0.2s ease",
            }}
            onMouseEnter={e => (e.currentTarget.style.background = "rgba(0,0,0,0.09)")}
            onMouseLeave={e => (e.currentTarget.style.background = "rgba(0,0,0,0.05)")}
          >
            <svg width="14" height="10" viewBox="0 0 14 10" fill="none" aria-hidden="true">
              <rect width="14" height="1.5" rx="0.75" fill="currentColor" />
              <rect y="4.25" width="9" height="1.5" rx="0.75" fill="currentColor" />
              <rect y="8.5" width="14" height="1.5" rx="0.75" fill="currentColor" />
            </svg>
          </button>
        </nav>
      </header>

      {/* ── Mobile overlay ────────────────────────────────────────────────── */}
      {isMobileMenuOpen && (
        <div
          className="fixed inset-0 z-[300] md:hidden flex flex-col"
          style={{
            background: "rgba(249,249,249,0.96)",
            backdropFilter: "saturate(180%) blur(28px)",
            WebkitBackdropFilter: "saturate(180%) blur(28px)",
          }}
        >
          <div className="flex items-center justify-between px-5 pt-5 pb-3">
            <span style={{
              fontFamily: "var(--font-display,'Syne',sans-serif)",
              fontSize: "16px", fontWeight: 700,
              letterSpacing: "-0.03em", color: "#0a0a0a",
            }}>
              Cortex
            </span>
            <button
              onClick={() => setMobileOpen(false)}
              aria-label="Close navigation menu"
              style={{
                width: 32, height: 32, borderRadius: "50%",
                background: "rgba(0,0,0,0.06)",
                border: "1px solid rgba(0,0,0,0.07)",
                display: "flex", alignItems: "center", justifyContent: "center",
                cursor: "pointer", transition: "background 0.2s ease",
              }}
              onMouseEnter={e => (e.currentTarget.style.background = "rgba(0,0,0,0.10)")}
              onMouseLeave={e => (e.currentTarget.style.background = "rgba(0,0,0,0.06)")}
            >
              <X style={{ width: 13, height: 13, color: "#0a0a0a" }} />
            </button>
          </div>

          <nav className="flex flex-col gap-1 px-4 mt-2 flex-1" aria-label="Mobile navigation">
            {navItems.map(({ href, label, id }) => {
              const isActive = activeSection === id
              return (
                <Link
                  key={href} href={href}
                  onClick={e => handleNavClick(e, href, id)}
                  style={{
                    display: "flex", alignItems: "center", justifyContent: "space-between",
                    padding: "13px 16px", borderRadius: "14px",
                    fontSize: "16px", fontWeight: isActive ? 600 : 400,
                    color: isActive ? "#fff" : "rgba(0,0,0,0.55)",
                    background: isActive ? "#0a0a0a" : "rgba(0,0,0,0.03)",
                    border: `1px solid ${isActive ? "transparent" : "rgba(0,0,0,0.05)"}`,
                    fontFamily: "var(--font-sans,'DM Sans',sans-serif)",
                    textDecoration: "none",
                    transition: "all 0.2s ease",
                    letterSpacing: "-0.01em",
                  }}
                >
                  {label}
                  {isActive && (
                    <span style={{
                      fontSize: "11px", opacity: 0.5,
                      letterSpacing: "0.05em",
                      fontFamily: "var(--font-mono)",
                    }}>●</span>
                  )}
                </Link>
              )
            })}
          </nav>

          <div className="px-4 pb-10 pt-4">
            <Link
              href="/dashboard"
              onClick={() => setMobileOpen(false)}
              style={{
                display: "flex", alignItems: "center", justifyContent: "center",
                width: "100%", padding: "14px",
                fontSize: "15px", fontWeight: 600,
                borderRadius: "14px",
                background: "#0a0a0a", color: "#fff",
                textDecoration: "none",
                boxShadow: "0 4px 16px rgba(0,0,0,0.16)",
                letterSpacing: "-0.01em",
                fontFamily: "var(--font-sans,'DM Sans',sans-serif)",
              }}
            >
              Launch App
            </Link>
          </div>
        </div>
      )}
    </>
  )
}
