"use client"

/**
 * PortfolioHeader — Liquid Glass pill navbar
 *
 * Motion upgrades (v2):
 *  - Active nav pill: Framer Motion layoutId="nav-active-pill" → spring slides
 *    between items instead of rAF-driven CSS transform
 *  - CTA button: whileHover spring lift, whileTap compress
 *  - Theme toggle: spring scale on hover
 *  - Mobile menu: AnimatePresence fade+slide-up entrance
 *  - prefers-reduced-motion: layoutId animation disabled, instant transitions
 */

import type React from "react"
import { useState, useEffect, useRef, useCallback } from "react"
import Link from "next/link"
import { X, LayoutDashboard } from "lucide-react"
import { DashboardLink } from "@/components/shared/DashboardLink"
import { motion, AnimatePresence, useReducedMotion } from "framer-motion"
import { SPRING, DURATION, EASE } from "@/lib/utils/motion"

// ── Nav items ──────────────────────────────────────────────────────────────

const navItems = [
  { href: "#works",        label: "Capabilities", id: "works"        },
  { href: "#about",        label: "About",         id: "about"        },
  { href: "#testimonials", label: "Artifacts",     id: "testimonials" },
  { href: "#awards",       label: "Stack",          id: "awards"       },
  { href: "#insights",     label: "Insights",       id: "insights"     },
]

// ── Motion presets ─────────────────────────────────────────────────────────

const CTA_HOVER = { y: -2, filter: "brightness(1.12)", transition: SPRING.snappy }
const CTA_TAP   = { scale: 0.96, y: 1, transition: { duration: DURATION.micro } }

const MOBILE_OVERLAY_VARIANTS = {
  hidden:  { opacity: 0, y: -8 },
  visible: { opacity: 1, y: 0, transition: { duration: DURATION.medium, ease: EASE.out } },
  exit:    { opacity: 0, y: -8, transition: { duration: DURATION.fast, ease: EASE.snap } },
}

// ── Component ──────────────────────────────────────────────────────────────

export function PortfolioHeader() {
  const [isMobileMenuOpen, setMobileOpen]  = useState(false)
  const [activeSection, setActiveSection]  = useState<string>("")
  const [isDark, setIsDark]                = useState(true)
  const [mounted, setMounted]              = useState(false)

  const navRef   = useRef<HTMLElement>(null)
  const glareRef = useRef<HTMLDivElement>(null)
  const prefersReduced = useReducedMotion()

  // ── Mount guard ───────────────────────────────────────────────────────────
  useEffect(() => { setMounted(true) }, [])

  // ── Theme sync ────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!mounted) return
    document.documentElement.setAttribute("data-theme", isDark ? "dark" : "light")
  }, [isDark, mounted])

  // ── Glare follow ─────────────────────────────────────────────────────────
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

  // ── Smooth scroll ─────────────────────────────────────────────────────────
  const handleNavClick = (e: React.MouseEvent<HTMLAnchorElement>, href: string, id: string) => {
    e.preventDefault()
    setActiveSection(id)
    const el = document.querySelector(href)
    if (el) {
      const top = el.getBoundingClientRect().top + window.pageYOffset - 80
      window.scrollTo({ top, behavior: "smooth" })
    }
    setMobileOpen(false)
  }

  // ── Theme tokens ──────────────────────────────────────────────────────────
  const glass = isDark
    ? {
        bg:         "rgba(10, 13, 22, 0.72)",
        border:     "rgba(255,255,255,0.08)",
        shadow:     "0 2px 40px rgba(0,0,0,0.55), 0 1px 12px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.09), inset 0 0 0 1px rgba(255,255,255,0.04)",
        reflection: "linear-gradient(180deg,rgba(255,255,255,0.10) 0%,rgba(255,255,255,0) 100%)",
        glare:      "rgba(96,239,255,0.20)",
        pill:       "rgba(255,255,255,0.09)",
        pillShadow: "0 2px 12px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.15)",
        iconColor:  "#8f9ba8",
        iconActive: "var(--primary, #00E5A8)",
        divider:    "rgba(255,255,255,0.09)",
      }
    : {
        bg:         "rgba(250, 252, 255, 0.78)",
        border:     "rgba(255,255,255,0.65)",
        shadow:     "0 2px 32px rgba(0,0,0,0.10), 0 1px 8px rgba(0,0,0,0.06), inset 0 1px 0 rgba(255,255,255,0.90), inset 0 0 0 1px rgba(255,255,255,0.55)",
        reflection: "linear-gradient(180deg,rgba(255,255,255,0.75) 0%,rgba(255,255,255,0) 100%)",
        glare:      "rgba(0,242,254,0.35)",
        pill:       "#ffffff",
        pillShadow: "0 2px 14px rgba(0,80,200,0.12), inset 0 1px 0 rgba(255,255,255,0.95)",
        iconColor:  "#4a5568",
        iconActive: "var(--primary, #009E6B)",
        divider:    "rgba(0,0,0,0.09)",
      }

  if (!mounted) return null

  return (
    <>
      {/* ── Header ──────────────────────────────────────────────────────── */}
      <header
        className="fixed top-0 left-0 right-0 z-[200] flex justify-center"
        style={{ pointerEvents: "none", paddingTop: "18px" }}
      >
        <nav
          ref={navRef}
          aria-label="Main navigation"
          onMouseMove={onMouseMove}
          style={{
            pointerEvents:     "auto",
            position:          "relative",
            display:           "flex",
            alignItems:        "center",
            padding:           "8px 12px",
            borderRadius:      "24px",
            background:        glass.bg,
            backdropFilter:    "blur(40px) saturate(220%)",
            WebkitBackdropFilter: "blur(40px) saturate(220%)",
            boxShadow:         glass.shadow,
            border:            `1px solid ${glass.border}`,
            transition:        "background 0.5s ease, box-shadow 0.5s ease, border-color 0.5s ease",
            overflow:          "visible",
          }}
        >
          {/* Top reflection sheen */}
          <div style={{
            position: "absolute", top: 1, left: 1, right: 1, height: "40%",
            borderRadius: "23px 23px 12px 12px",
            background: glass.reflection,
            pointerEvents: "none", zIndex: 6,
            transition: "background 0.5s ease",
          }} />

          {/* Mouse-follow glare */}
          <div style={{ position: "absolute", inset: 0, borderRadius: 24, overflow: "hidden", pointerEvents: "none", zIndex: 5 }}>
            <div
              ref={glareRef}
              className="liquid-glare"
              style={{
                position: "absolute", inset: 0,
                background: `radial-gradient(circle 120px at var(--x,50%) var(--y,50%), ${glass.glare} 0%, transparent 100%)`,
                mixBlendMode: "overlay", opacity: 0,
                transition: "opacity 0.3s ease",
              }}
            />
          </div>

          {/* Logo */}
          <Link
            href="#"
            onClick={e => { e.preventDefault(); setActiveSection(""); window.scrollTo({ top: 0, behavior: "smooth" }) }}
            aria-label="Cortex — back to top"
            style={{
              position: "relative", zIndex: 3,
              display: "flex", alignItems: "center", gap: "8px",
              padding: "6px 14px 6px 8px",
              borderRadius: "16px", textDecoration: "none",
              transition: "background 0.2s ease",
            }}
            onMouseEnter={e => (e.currentTarget.style.background = "rgba(0,0,0,0.06)")}
            onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
          >
            <span style={{
              width: 26, height: 26, borderRadius: "8px",
              background: isDark ? "rgba(0,229,168,0.12)" : "#0a0a0a",
              display: "inline-flex", alignItems: "center", justifyContent: "center",
              flexShrink: 0,
              border: isDark ? "1px solid rgba(0,229,168,0.22)" : "none",
              boxShadow: isDark
                ? "0 0 10px rgba(0,229,168,0.12), inset 0 1px 0 rgba(255,255,255,0.12)"
                : "0 1px 4px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.12)",
              transition: "background 0.4s ease",
            }}>
              <LayoutDashboard style={{ width: 12, height: 12, color: isDark ? "var(--primary, #00E5A8)" : "#fff" }} />
            </span>
            <span style={{
              fontFamily: "var(--font-display,'Syne',sans-serif)",
              fontSize: "14px", fontWeight: 700, letterSpacing: "-0.03em",
              color: isDark ? "rgba(255,255,255,0.9)" : "#0a0a0a",
              transition: "color 0.4s ease",
            }}>
              Cortex
            </span>
          </Link>

          {/* ── Desktop nav — Framer Motion layoutId pill ─────────────── */}
          <div
            className="hidden md:flex items-center"
            role="list"
            style={{ position: "relative", display: "flex", gap: "2px", zIndex: 3 }}
          >
            {navItems.map(({ href, label, id }) => {
              const isActive = activeSection === id
              return (
                <Link
                  key={href}
                  href={href}
                  role="listitem"
                  onClick={e => handleNavClick(e, href, id)}
                  style={{
                    position: "relative",
                    display: "flex", alignItems: "center",
                    padding: "0 16px",
                    height: "40px",
                    borderRadius: "14px",
                    fontSize: "14px", fontWeight: 500,
                    letterSpacing: "0.3px",
                    color: isActive ? glass.iconActive : glass.iconColor,
                    textDecoration: "none",
                    whiteSpace: "nowrap",
                    fontFamily: "var(--font-sans,'Inter',system-ui,sans-serif)",
                    transition: "color 0.25s ease",
                    zIndex: 2,
                  }}
                >
                  {/* Spring-animated active background pill */}
                  {isActive && !prefersReduced && (
                    <motion.span
                      layoutId="nav-active-pill"
                      style={{
                        position: "absolute", inset: 0,
                        borderRadius: "14px",
                        background: glass.pill,
                        boxShadow: glass.pillShadow,
                        backdropFilter: "blur(8px)",
                        WebkitBackdropFilter: "blur(8px)",
                        zIndex: -1,
                      }}
                      transition={SPRING.gentle}
                      aria-hidden
                    />
                  )}
                  {/* CSS-only fallback for reduced-motion */}
                  {isActive && prefersReduced && (
                    <span
                      style={{
                        position: "absolute", inset: 0,
                        borderRadius: "14px",
                        background: glass.pill,
                        boxShadow: glass.pillShadow,
                        zIndex: -1,
                      }}
                      aria-hidden
                    />
                  )}
                  {label}
                </Link>
              )
            })}
          </div>

          {/* Divider */}
          <div style={{
            width: "1px", height: "22px",
            background: glass.divider,
            margin: "0 8px", zIndex: 3,
            transition: "background 0.5s ease",
          }} />

          {/* Theme toggle */}
          <motion.button
            onClick={() => setIsDark(d => !d)}
            aria-label="Toggle theme"
            whileHover={prefersReduced ? {} : { scale: 1.08, transition: SPRING.snappy }}
            whileTap={prefersReduced ? {} : { scale: 0.92 }}
            style={{
              position: "relative", zIndex: 3,
              background: "transparent", border: "none",
              width: "42px", height: "42px", borderRadius: "14px",
              color: glass.iconColor, cursor: "pointer",
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
              <svg style={{
                position: "absolute", top: 0, left: 0, strokeWidth: 2.2,
                transition: "transform 0.5s cubic-bezier(0.34,1.2,0.64,1), opacity 0.4s ease",
                opacity: isDark ? 0 : 1,
                transform: isDark ? "rotate(90deg) scale(0)" : "rotate(0deg) scale(1)",
              }} width="18" height="18" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="5" />
                <line x1="12" y1="1" x2="12" y2="3" /><line x1="12" y1="21" x2="12" y2="23" />
                <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" /><line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
                <line x1="1" y1="12" x2="3" y2="12" /><line x1="21" y1="12" x2="23" y2="12" />
                <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" /><line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
              </svg>
              {/* Moon */}
              <svg style={{
                position: "absolute", top: 0, left: 0, strokeWidth: 2.2,
                transition: "transform 0.5s cubic-bezier(0.34,1.2,0.64,1), opacity 0.4s ease",
                opacity: isDark ? 1 : 0,
                transform: isDark ? "rotate(0deg) scale(1)" : "rotate(-90deg) scale(0)",
              }} width="18" height="18" viewBox="0 0 24 24" fill="none"
                stroke="currentColor" strokeLinecap="round" strokeLinejoin="round">
                <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
              </svg>
            </div>
          </motion.button>

          {/* CTA — spring lift on hover */}
          <motion.div
            style={{ position: "relative", zIndex: 3, marginLeft: "4px" }}
            whileHover={prefersReduced ? {} : CTA_HOVER}
            whileTap={prefersReduced ? {} : CTA_TAP}
            className="hidden md:block"
          >
            <DashboardLink
              style={{
                display: "inline-flex", alignItems: "center", justifyContent: "center",
                padding: "8px 18px", borderRadius: "16px",
                background: isDark
                  ? "linear-gradient(135deg, var(--primary, #00E5A8) 0%, #00c9a7 100%)"
                  : "#0a0a0a",
                color: isDark ? "#060810" : "#fff",
                fontSize: "13px", fontWeight: 600,
                textDecoration: "none", letterSpacing: "-0.01em",
                border: "none",
                boxShadow: isDark
                  ? "0 4px 16px rgba(0,229,168,0.25), inset 0 1px 0 rgba(255,255,255,0.22)"
                  : "0 1px 6px rgba(0,0,0,0.24), inset 0 1px 0 rgba(255,255,255,0.10)",
                whiteSpace: "nowrap",
                fontFamily: "var(--font-sans,'Inter',sans-serif)",
              }}
            >
              Launch App
            </DashboardLink>
          </motion.div>

          {/* Mobile burger */}
          <motion.button
            onClick={() => setMobileOpen(true)}
            className="md:hidden flex items-center justify-center"
            aria-label="Open navigation menu"
            whileTap={prefersReduced ? {} : { scale: 0.92 }}
            style={{
              marginLeft: "4px", width: 36, height: 36, borderRadius: "12px",
              background: isDark ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.05)",
              border: `1px solid ${glass.border}`,
              cursor: "pointer", color: glass.iconColor,
              zIndex: 3, position: "relative", flexShrink: 0,
            }}
          >
            <svg width="14" height="10" viewBox="0 0 14 10" fill="none" aria-hidden="true">
              <rect width="14" height="1.5" rx="0.75" fill="currentColor" />
              <rect y="4.25" width="9" height="1.5" rx="0.75" fill="currentColor" />
              <rect y="8.5" width="14" height="1.5" rx="0.75" fill="currentColor" />
            </svg>
          </motion.button>
        </nav>
      </header>

      {/* Glare CSS */}
      <style dangerouslySetInnerHTML={{ __html: `nav:hover .liquid-glare { opacity: 1 !important; }` }} />

      {/* ── Mobile overlay — AnimatePresence enter/exit ──────────────────── */}
      <AnimatePresence>
        {isMobileMenuOpen && (
          <motion.div
            key="mobile-menu"
            variants={MOBILE_OVERLAY_VARIANTS}
            initial="hidden"
            animate="visible"
            exit="exit"
            className="fixed inset-0 z-[300] md:hidden flex flex-col"
            style={{
              background: isDark ? "rgba(5,5,8,0.97)" : "rgba(249,249,249,0.97)",
              backdropFilter: "saturate(180%) blur(28px)",
              WebkitBackdropFilter: "saturate(180%) blur(28px)",
            }}
          >
            <div className="flex items-center justify-between px-5 pt-5 pb-3">
              <span style={{
                fontFamily: "var(--font-display,'Syne',sans-serif)",
                fontSize: "16px", fontWeight: 700, letterSpacing: "-0.03em",
                color: isDark ? "#fff" : "#0a0a0a",
              }}>
                Cortex
              </span>
              <motion.button
                onClick={() => setMobileOpen(false)}
                aria-label="Close navigation menu"
                whileTap={prefersReduced ? {} : { scale: 0.88 }}
                style={{
                  width: 32, height: 32, borderRadius: "50%",
                  background: isDark ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.06)",
                  border: `1px solid ${glass.border}`,
                  display: "flex", alignItems: "center", justifyContent: "center",
                  cursor: "pointer",
                }}
              >
                <X style={{ width: 13, height: 13, color: isDark ? "#fff" : "#0a0a0a" }} />
              </motion.button>
            </div>

            <nav className="flex flex-col gap-1 px-4 mt-2 flex-1" aria-label="Mobile navigation">
              {navItems.map(({ href, label, id }, i) => {
                const isActive = activeSection === id
                return (
                  <motion.div
                    key={href}
                    initial={prefersReduced ? false : { opacity: 0, x: -16 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ duration: DURATION.medium, delay: i * 0.05, ease: EASE.out }}
                  >
                    <Link
                      href={href}
                      onClick={e => handleNavClick(e, href, id)}
                      style={{
                        display: "flex", alignItems: "center", justifyContent: "space-between",
                        padding: "13px 16px", borderRadius: "14px",
                        fontSize: "16px", fontWeight: isActive ? 600 : 400,
                        color: isActive
                          ? (isDark ? "var(--primary, #00E5A8)" : "#fff")
                          : (isDark ? "rgba(240,244,255,0.50)" : "rgba(0,0,0,0.55)"),
                        background: isActive
                          ? (isDark ? "rgba(0,229,168,0.10)" : "#0a0a0a")
                          : (isDark ? "rgba(255,255,255,0.04)" : "rgba(0,0,0,0.03)"),
                        border: `1px solid ${isActive ? "rgba(0,229,168,0.25)" : glass.border}`,
                        fontFamily: "var(--font-sans,'Inter',sans-serif)",
                        textDecoration: "none",
                        transition: "all 0.2s ease",
                      }}
                    >
                      {label}
                      {isActive && <span style={{ fontSize: "11px", opacity: 0.5 }}>●</span>}
                    </Link>
                  </motion.div>
                )
              })}
            </nav>

            <div className="px-4 pb-10 pt-4">
              <motion.div
                whileHover={prefersReduced ? {} : CTA_HOVER}
                whileTap={prefersReduced ? {} : CTA_TAP}
              >
                <DashboardLink
                  onClick={() => setMobileOpen(false)}
                  style={{
                    display: "flex", alignItems: "center", justifyContent: "center",
                    width: "100%", padding: "14px",
                    fontSize: "15px", fontWeight: 600, borderRadius: "14px",
                    background: isDark
                      ? "linear-gradient(135deg, var(--primary, #00E5A8) 0%, #00c9a7 100%)"
                      : "#0a0a0a",
                    color: isDark ? "#060810" : "#fff",
                    textDecoration: "none", border: "none",
                    boxShadow: isDark ? "0 4px 20px rgba(0,229,168,0.25)" : "0 4px 16px rgba(0,0,0,0.16)",
                    letterSpacing: "-0.01em",
                    fontFamily: "var(--font-sans,'Inter',sans-serif)",
                  }}
                >
                  Launch App
                </DashboardLink>
              </motion.div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}
