"use client"

import type React from "react"
import { useState, useEffect, useRef, useCallback } from "react"
import Link from "next/link"
import { X, LayoutDashboard } from "lucide-react"

// =============================================================================
// PortfolioHeader — Cyber-Aurora Liquid Glass pill navbar
//
// Design from index_new.html:
//  • Floating pill housing with glassmorphism backdrop
//  • Active item slides a white pill underneath (animated via rAF)
//  • Glare overlay tracks mouse position on hover
//  • Theme toggle (light ↔ dark) with sun/moon crossfade
//  • Animated blob background via CSS custom properties
// =============================================================================

const navItems = [
  { href: "#works",        label: "Capabilities", id: "works"        },
  { href: "#about",        label: "About",         id: "about"        },
  { href: "#testimonials", label: "Artifacts",     id: "testimonials" },
  { href: "#awards",       label: "Stack",          id: "awards"       },
  { href: "#insights",     label: "Insights",       id: "insights"     },
]

export function PortfolioHeader() {
  const [isMobileMenuOpen, setMobileOpen] = useState(false)
  const [activeSection, setActiveSection]  = useState<string>("")
  const [isDark, setIsDark]                = useState(true)
  const [mounted, setMounted]              = useState(false)

  const navRef       = useRef<HTMLElement>(null)
  const glareRef     = useRef<HTMLDivElement>(null)
  const activePillRef = useRef<HTMLDivElement>(null)
  const btnRefs      = useRef<Map<string, HTMLButtonElement>>(new Map())
  const headerRef    = useRef<HTMLElement>(null)

  // ── Mount guard (avoids SSR mismatch) ─────────────────────────────────────
  useEffect(() => { setMounted(true) }, [])

  // ── Theme: sync with html[data-theme] ─────────────────────────────────────
  useEffect(() => {
    if (!mounted) return
    const root = document.documentElement
    root.setAttribute("data-theme", isDark ? "dark" : "light")
  }, [isDark, mounted])

  // ── Active-pill sliding animation ─────────────────────────────────────────
  const updatePill = useCallback((id: string, animate = true) => {
    const btn  = btnRefs.current.get(id)
    const pill = activePillRef.current
    if (!btn || !pill) return

    if (!animate) {
      pill.style.transition = "none"
    } else {
      pill.style.transition =
        "transform 0.45s cubic-bezier(0.16,1,0.3,1), width 0.45s cubic-bezier(0.16,1,0.3,1)"
    }

    pill.style.width     = `${btn.offsetWidth}px`
    pill.style.transform = `translateX(${btn.offsetLeft}px)`

    // Re-enable transition after a forced reflow so the "no-animate" snap sticks
    if (!animate) {
      void pill.offsetWidth
      pill.style.transition =
        "transform 0.45s cubic-bezier(0.16,1,0.3,1), width 0.45s cubic-bezier(0.16,1,0.3,1)"
    }
  }, [])

  // Initial pill position on mount (after refs are set)
  useEffect(() => {
    if (!mounted) return
    const initial = activeSection || navItems[0]?.id
    if (initial) setTimeout(() => updatePill(initial, false), 60)
  }, [mounted, activeSection, updatePill])

  useEffect(() => {
    if (activeSection) updatePill(activeSection)
  }, [activeSection, updatePill])

  // ── Glare: radial light that follows the mouse ─────────────────────────────
  const onMouseMove = useCallback((e: React.MouseEvent<HTMLElement>) => {
    const glare = glareRef.current
    const nav   = navRef.current
    if (!glare || !nav) return
    const rect = nav.getBoundingClientRect()
    glare.style.setProperty("--x", `${e.clientX - rect.left}px`)
    glare.style.setProperty("--y", `${e.clientY - rect.top}px`)
  }, [])

  // ── Section observer ──────────────────────────────────────────────────────
  useEffect(() => {
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
    return () => observers.forEach(o => o.disconnect())
  }, [])

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
      const top = el.getBoundingClientRect().top + window.pageYOffset - 80
      window.scrollTo({ top, behavior: "smooth" })
    }
    setMobileOpen(false)
  }

  // ── Resize: re-snap pill ─────────────────────────────────────────────────
  useEffect(() => {
    const onResize = () => {
      const id = activeSection || navItems[0]?.id
      if (id) updatePill(id, false)
    }
    window.addEventListener("resize", onResize)
    return () => window.removeEventListener("resize", onResize)
  }, [activeSection, updatePill])

  // ── Theme-aware pill & icon colors ────────────────────────────────────────
  // These mirror the CSS variables in index_new.html exactly.
  const glass = isDark
    ? {
        bg:        "rgba(18,18,26,0.55)",
        border:    "rgba(255,255,255,0.08)",
        shadow:    "0 30px 60px -15px rgba(0,0,0,0.7), inset 0 1px 2px rgba(255,255,255,0.15), inset 0 -1px 3px rgba(0,255,135,0.08), 0 0 0 1px rgba(255,255,255,0.08)",
        reflection: "linear-gradient(180deg,rgba(255,255,255,0.12) 0%,rgba(255,255,255,0) 100%)",
        glare:     "rgba(96,239,255,0.25)",
        pill:      "linear-gradient(135deg,rgba(255,255,255,0.10) 0%,rgba(255,255,255,0.03) 100%)",
        pillShadow:"0 8px 32px rgba(0,0,0,0.5), inset 0 1px 1px rgba(255,255,255,0.2), 0 0 15px rgba(0,255,135,0.15)",
        iconColor: "#8f9ba8",
        iconActive:"#00ff87",
        divider:   "rgba(255,255,255,0.10)",
      }
    : {
        bg:        "rgba(255,255,255,0.25)",
        border:    "rgba(255,255,255,0.60)",
        shadow:    "0 30px 60px -15px rgba(0,120,255,0.12), inset 0 1px 2px rgba(255,255,255,0.9), inset 0 -1px 3px rgba(0,242,254,0.2), 0 0 0 1px rgba(255,255,255,0.60)",
        reflection: "linear-gradient(180deg,rgba(255,255,255,0.7) 0%,rgba(255,255,255,0) 100%)",
        glare:     "rgba(0,242,254,0.4)",
        pill:      "linear-gradient(135deg,#ffffff 0%,#e2eafc 100%)",
        pillShadow:"0 8px 20px rgba(0,100,255,0.15), inset 0 1px 2px rgba(255,255,255,0.9)",
        iconColor: "#4a5568",
        iconActive:"#0066ff",
        divider:   "rgba(0,0,0,0.10)",
      }

  if (!mounted) return null

  return (
    <>
      {/* ── Header ──────────────────────────────────────────────────────── */}
      <header
        ref={headerRef}
        className="fixed top-0 left-0 right-0 z-[200] flex justify-center"
        style={{ pointerEvents: "none", paddingTop: "18px" }}
      >
        <nav
          ref={navRef}
          aria-label="Main navigation"
          onMouseMove={onMouseMove}
          style={{
            pointerEvents: "auto",
            position: "relative",
            display: "flex",
            alignItems: "center",
            padding: "8px 12px",
            borderRadius: "24px",
            background: glass.bg,
            backdropFilter: "blur(40px) saturate(220%)",
            WebkitBackdropFilter: "blur(40px) saturate(220%)",
            boxShadow: glass.shadow,
            border: `1px solid ${glass.border}`,
            transition: "background 0.5s ease, box-shadow 0.5s ease, border-color 0.5s ease",
            overflow: "visible",
          }}
        >
          {/* ── Top reflection sheen ──────────────────────────────────── */}
          <div style={{
            position: "absolute",
            top: 1, left: 1, right: 1, height: "40%",
            borderRadius: "23px 23px 12px 12px",
            background: glass.reflection,
            pointerEvents: "none",
            zIndex: 6,
            transition: "background 0.5s ease",
          }} />

          {/* ── Mouse-follow glare ────────────────────────────────────── */}
          <div style={{
            position: "absolute", inset: 0, borderRadius: 24,
            overflow: "hidden", pointerEvents: "none", zIndex: 5,
          }}>
            <div
              ref={glareRef}
              style={{
                position: "absolute", inset: 0,
                background: `radial-gradient(circle 120px at var(--x,50%) var(--y,50%), ${glass.glare} 0%, transparent 100%)`,
                mixBlendMode: "overlay",
                opacity: 0,
                transition: "opacity 0.3s ease",
              }}
              className="liquid-glare"
            />
          </div>

          {/* ── Logo ─────────────────────────────────────────────────── */}
          <Link
            href="#"
            onClick={e => {
              e.preventDefault()
              setActiveSection("")
              window.scrollTo({ top: 0, behavior: "smooth" })
            }}
            aria-label="Cortex — back to top"
            style={{
              position: "relative", zIndex: 3,
              display: "flex", alignItems: "center", gap: "8px",
              padding: "6px 14px 6px 8px",
              borderRadius: "16px",
              textDecoration: "none",
              transition: "background 0.2s ease",
            }}
            onMouseEnter={e => (e.currentTarget.style.background = "rgba(0,0,0,0.06)")}
            onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
          >
            <span style={{
              width: 26, height: 26, borderRadius: "8px",
              background: isDark ? "rgba(255,255,255,0.1)" : "#0a0a0a",
              display: "inline-flex", alignItems: "center", justifyContent: "center",
              flexShrink: 0,
              boxShadow: isDark
                ? "inset 0 1px 0 rgba(255,255,255,0.15)"
                : "0 1px 4px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.12)",
              transition: "background 0.4s ease",
            }}>
              <LayoutDashboard style={{ width: 12, height: 12, color: isDark ? "#00ff87" : "#fff" }} />
            </span>
            <span style={{
              fontFamily: "var(--font-display,'Syne',sans-serif)",
              fontSize: "14px", fontWeight: 700,
              letterSpacing: "-0.03em",
              color: isDark ? "rgba(255,255,255,0.9)" : "#0a0a0a",
              transition: "color 0.4s ease",
            }}>
              Cortex
            </span>
          </Link>

          {/* ── Desktop nav items with sliding pill ───────────────────── */}
          <div
            className="hidden md:flex items-center"
            role="list"
            style={{ position: "relative", display: "flex", gap: "6px", zIndex: 3 }}
          >
            {/* The sliding active pill */}
            <div
              ref={activePillRef}
              style={{
                position: "absolute",
                top: 0, left: 0,
                height: "44px",
                background: glass.pill,
                borderRadius: "16px",
                boxShadow: glass.pillShadow,
                transition: "transform 0.45s cubic-bezier(0.16,1,0.3,1), width 0.45s cubic-bezier(0.16,1,0.3,1)",
                zIndex: 1,
                pointerEvents: "none",
              }}
            />

            {navItems.map(({ href, label, id }) => {
              const isActive = activeSection === id
              return (
                <Link
                  key={href}
                  href={href}
                  role="listitem"
                  onClick={e => handleNavClick(e, href, id)}
                  style={{
                    position: "relative", zIndex: 2,
                    display: "flex", alignItems: "center",
                    padding: "0 18px",
                    height: "44px",
                    borderRadius: "16px",
                    fontSize: "14px",
                    fontWeight: 500,
                    letterSpacing: "0.3px",
                    color: isActive ? glass.iconActive : glass.iconColor,
                    textDecoration: "none",
                    whiteSpace: "nowrap",
                    fontFamily: "var(--font-sans,'DM Sans',sans-serif)",
                    transition: "color 0.3s ease",
                    background: "transparent",
                    border: "none",
                    cursor: "pointer",
                  }}
                  ref={el => {
                    if (el) btnRefs.current.set(id, el as unknown as HTMLButtonElement)
                  }}
                >
                  <span style={{
                    display: "flex", alignItems: "center", gap: "8px",
                    transition: "transform 0.2s cubic-bezier(0.32,0.72,0,1)",
                  }}>
                    {label}
                  </span>
                </Link>
              )
            })}
          </div>

          {/* ── Divider ──────────────────────────────────────────────── */}
          <div style={{
            width: "1px", height: "22px",
            background: glass.divider,
            margin: "0 8px",
            zIndex: 3,
            transition: "background 0.5s ease",
          }} />

          {/* ── Theme toggle ─────────────────────────────────────────── */}
          <button
            onClick={() => setIsDark(d => !d)}
            aria-label="Toggle theme"
            style={{
              position: "relative", zIndex: 3,
              background: "transparent",
              border: "none",
              width: "42px", height: "42px",
              borderRadius: "14px",
              color: glass.iconColor,
              cursor: "pointer",
              display: "flex", alignItems: "center", justifyContent: "center",
              transition: "color 0.3s ease, background 0.3s ease",
            }}
            onMouseEnter={e => {
              e.currentTarget.style.background = glass.border
              e.currentTarget.style.color = glass.iconActive
            }}
            onMouseLeave={e => {
              e.currentTarget.style.background = "transparent"
              e.currentTarget.style.color = glass.iconColor
            }}
          >
            <div style={{ position: "relative", width: 18, height: 18, pointerEvents: "none" }}>
              {/* Sun */}
              <svg
                style={{
                  position: "absolute", top: 0, left: 0,
                  transition: "transform 0.5s cubic-bezier(0.34,1.2,0.64,1), opacity 0.4s ease",
                  opacity: isDark ? 0 : 1,
                  transform: isDark ? "rotate(90deg) scale(0)" : "rotate(0deg) scale(1)",
                  strokeWidth: 2.2,
                }}
                width="18" height="18" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" strokeLinecap="round" strokeLinejoin="round"
              >
                <circle cx="12" cy="12" r="5" />
                <line x1="12" y1="1" x2="12" y2="3" />
                <line x1="12" y1="21" x2="12" y2="23" />
                <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
                <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
                <line x1="1" y1="12" x2="3" y2="12" />
                <line x1="21" y1="12" x2="23" y2="12" />
                <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
                <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
              </svg>
              {/* Moon */}
              <svg
                style={{
                  position: "absolute", top: 0, left: 0,
                  transition: "transform 0.5s cubic-bezier(0.34,1.2,0.64,1), opacity 0.4s ease",
                  opacity: isDark ? 1 : 0,
                  transform: isDark ? "rotate(0deg) scale(1)" : "rotate(-90deg) scale(0)",
                  strokeWidth: 2.2,
                }}
                width="18" height="18" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" strokeLinecap="round" strokeLinejoin="round"
              >
                <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
              </svg>
            </div>
          </button>

          {/* ── CTA ───────────────────────────────────────────────────── */}
          <Link
            href="/dashboard"
            className="hidden md:inline-flex items-center justify-center"
            style={{
              marginLeft: "4px",
              padding: "8px 18px",
              borderRadius: "16px",
              background: isDark
                ? "linear-gradient(135deg,rgba(0,255,135,0.18) 0%,rgba(96,239,255,0.14) 100%)"
                : "#0a0a0a",
              color: isDark ? "#00ff87" : "#fff",
              fontSize: "13px",
              fontWeight: 600,
              textDecoration: "none",
              letterSpacing: "-0.01em",
              border: isDark ? "1px solid rgba(0,255,135,0.25)" : "none",
              boxShadow: isDark
                ? "0 0 20px rgba(0,255,135,0.15), inset 0 1px 0 rgba(255,255,255,0.12)"
                : "0 1px 6px rgba(0,0,0,0.24), inset 0 1px 0 rgba(255,255,255,0.10)",
              whiteSpace: "nowrap",
              fontFamily: "var(--font-sans,'DM Sans',sans-serif)",
              zIndex: 3,
              position: "relative",
              transition: "all 0.3s ease",
            }}
            onMouseEnter={e => {
              e.currentTarget.style.filter = "brightness(1.15)"
            }}
            onMouseLeave={e => {
              e.currentTarget.style.filter = ""
            }}
          >
            Launch App
          </Link>

          {/* ── Mobile burger ────────────────────────────────────────── */}
          <button
            onClick={() => setMobileOpen(true)}
            className="md:hidden flex items-center justify-center"
            aria-label="Open navigation menu"
            style={{
              marginLeft: "4px",
              width: 36, height: 36, borderRadius: "12px",
              background: isDark ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.05)",
              border: `1px solid ${glass.border}`,
              cursor: "pointer",
              color: glass.iconColor,
              zIndex: 3,
              position: "relative",
              flexShrink: 0,
              transition: "background 0.2s ease",
            }}
          >
            <svg width="14" height="10" viewBox="0 0 14 10" fill="none" aria-hidden="true">
              <rect width="14" height="1.5" rx="0.75" fill="currentColor" />
              <rect y="4.25" width="9" height="1.5" rx="0.75" fill="currentColor" />
              <rect y="8.5" width="14" height="1.5" rx="0.75" fill="currentColor" />
            </svg>
          </button>
        </nav>
      </header>

      {/* ── CSS for glare hover ──────────────────────────────────────────── */}
      <style>{`
        nav:hover .liquid-glare { opacity: 1 !important; }
      `}</style>

      {/* ── Mobile overlay ─────────────────────────────────────────────── */}
      {isMobileMenuOpen && (
        <div
          className="fixed inset-0 z-[300] md:hidden flex flex-col"
          style={{
            background: isDark ? "rgba(5,5,8,0.96)" : "rgba(249,249,249,0.96)",
            backdropFilter: "saturate(180%) blur(28px)",
            WebkitBackdropFilter: "saturate(180%) blur(28px)",
          }}
        >
          <div className="flex items-center justify-between px-5 pt-5 pb-3">
            <span style={{
              fontFamily: "var(--font-display,'Syne',sans-serif)",
              fontSize: "16px", fontWeight: 700,
              letterSpacing: "-0.03em",
              color: isDark ? "#fff" : "#0a0a0a",
            }}>
              Cortex
            </span>
            <button
              onClick={() => setMobileOpen(false)}
              aria-label="Close navigation menu"
              style={{
                width: 32, height: 32, borderRadius: "50%",
                background: isDark ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.06)",
                border: `1px solid ${glass.border}`,
                display: "flex", alignItems: "center", justifyContent: "center",
                cursor: "pointer",
              }}
            >
              <X style={{ width: 13, height: 13, color: isDark ? "#fff" : "#0a0a0a" }} />
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
                    color: isActive
                      ? (isDark ? "#00ff87" : "#fff")
                      : (isDark ? "rgba(255,255,255,0.5)" : "rgba(0,0,0,0.55)"),
                    background: isActive
                      ? (isDark ? "rgba(0,255,135,0.12)" : "#0a0a0a")
                      : (isDark ? "rgba(255,255,255,0.04)" : "rgba(0,0,0,0.03)"),
                    border: `1px solid ${isActive ? glass.iconActive + "30" : glass.border}`,
                    fontFamily: "var(--font-sans,'DM Sans',sans-serif)",
                    textDecoration: "none",
                    transition: "all 0.2s ease",
                  }}
                >
                  {label}
                  {isActive && <span style={{ fontSize: "11px", opacity: 0.5 }}>●</span>}
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
                background: isDark
                  ? "linear-gradient(135deg,rgba(0,255,135,0.2) 0%,rgba(96,239,255,0.15) 100%)"
                  : "#0a0a0a",
                color: isDark ? "#00ff87" : "#fff",
                textDecoration: "none",
                border: isDark ? "1px solid rgba(0,255,135,0.3)" : "none",
                boxShadow: isDark ? "0 0 24px rgba(0,255,135,0.2)" : "0 4px 16px rgba(0,0,0,0.16)",
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
