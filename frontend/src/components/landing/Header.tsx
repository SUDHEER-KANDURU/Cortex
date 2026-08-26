"use client"

import type React from "react"
import { useState, useEffect, useRef, useCallback } from "react"
import Link from "next/link"
import { X, LayoutDashboard } from "lucide-react"
import { DashboardLink } from "@/components/shared/DashboardLink"
import { motion, AnimatePresence, useReducedMotion } from "framer-motion"
import { SPRING, DURATION, EASE } from "@/lib/utils/motion"

const navItems = [
  { href: "#works",        label: "Capabilities", id: "works"        },
  { href: "#about",        label: "About",         id: "about"        },
  { href: "#testimonials", label: "Artifacts",     id: "testimonials" },
  { href: "#awards",       label: "Stack",          id: "awards"       },
  { href: "#insights",     label: "Insights",       id: "insights"     },
]

const CTA_HOVER = { y: -2, filter: "brightness(1.08)", transition: SPRING.snappy }
const CTA_TAP   = { scale: 0.96, y: 1, transition: { duration: DURATION.micro } }

const MOBILE_OVERLAY_VARIANTS = {
  hidden:  { opacity: 0, y: -8 },
  visible: { opacity: 1, y: 0, transition: { duration: DURATION.medium, ease: EASE.out } },
  exit:    { opacity: 0, y: -8, transition: { duration: DURATION.fast, ease: EASE.snap } },
}

// ── Static liquid glass tokens — light only ──────────────────────────────
const glass = {
  bg:         "rgba(255, 255, 255, 0.22)",
  border:     "rgba(255, 255, 255, 0.55)",
  shadow:
    "0 8px 40px rgba(80,60,20,0.14)," +
    "0 2px 8px rgba(80,60,20,0.07)," +
    "inset 0 1px 0 rgba(255,255,255,0.80)," +
    "inset 0 -1px 0 rgba(255,255,255,0.25)," +
    "inset 0 0 0 0.5px rgba(255,255,255,0.45)",
  reflection: "linear-gradient(180deg,rgba(255,255,255,0.65) 0%,rgba(255,255,255,0) 100%)",
  glare:      "rgba(245,195,58,0.22)",
  iconColor:  "rgba(60,54,48,0.60)",
  iconActive: "#0F1923",
  divider:    "rgba(255,255,255,0.45)",
}

export function PortfolioHeader() {
  const [isMobileMenuOpen, setMobileOpen] = useState(false)
  const [activeSection, setActiveSection] = useState<string>("")
  const [mounted, setMounted]             = useState(false)

  const navRef   = useRef<HTMLElement>(null)
  const glareRef = useRef<HTMLDivElement>(null)
  const prefersReduced = useReducedMotion()

  useEffect(() => { setMounted(true) }, [])

  // Glare follow
  const onMouseMove = useCallback((e: React.MouseEvent<HTMLElement>) => {
    const glare = glareRef.current
    const nav   = navRef.current
    if (!glare || !nav) return
    const rect = nav.getBoundingClientRect()
    glare.style.setProperty("--x", `${e.clientX - rect.left}px`)
    glare.style.setProperty("--y", `${e.clientY - rect.top}px`)
  }, [])

  // Section observer
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

  // Smooth scroll
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

  if (!mounted) return null

  return (
    <>
      <header
        className="fixed top-0 left-0 right-0 z-[200] flex justify-center"
        style={{ pointerEvents: "none", paddingTop: "18px" }}
      >
        <nav
          ref={navRef}
          aria-label="Main navigation"
          onMouseMove={onMouseMove}
          style={{
            pointerEvents:        "auto",
            position:             "relative",
            display:              "flex",
            alignItems:           "center",
            padding:              "8px 12px",
            borderRadius:         "28px",
            background:           glass.bg,
            backdropFilter:       "blur(60px) saturate(240%) brightness(1.06)",
            WebkitBackdropFilter: "blur(60px) saturate(240%) brightness(1.06)",
            boxShadow:            glass.shadow,
            border:               `0.5px solid ${glass.border}`,
            overflow:             "visible",
          }}
        >
          {/* Top reflection sheen */}
          <div style={{
            position: "absolute", top: 1, left: 1, right: 1, height: "36%",
            borderRadius: "27px 27px 10px 10px",
            background: glass.reflection,
            pointerEvents: "none", zIndex: 6,
          }} />

          {/* Mouse-follow glare */}
          <div style={{ position: "absolute", inset: 0, borderRadius: 28, overflow: "hidden", pointerEvents: "none", zIndex: 5 }}>
            <div
              ref={glareRef}
              className="liquid-glare"
              style={{
                position: "absolute", inset: 0,
                background: `radial-gradient(circle 140px at var(--x,50%) var(--y,50%), ${glass.glare} 0%, transparent 100%)`,
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
              borderRadius: "18px", textDecoration: "none",
              transition: "background 0.2s ease",
            }}
            onMouseEnter={e => (e.currentTarget.style.background = "rgba(255,255,255,0.35)")}
            onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
          >
            <span style={{
              width: 26, height: 26, borderRadius: "8px",
              background: "rgba(30,42,56,0.12)",
              display: "inline-flex", alignItems: "center", justifyContent: "center",
              flexShrink: 0,
              border: "0.5px solid rgba(30,42,56,0.18)",
              boxShadow: "inset 0 1px 3px rgba(255,255,255,0.40)",
            }}>
              <LayoutDashboard style={{ width: 12, height: 12, color: "#1E2A38" }} />
            </span>
            <span style={{
              fontFamily: "var(--font-display,'Syne',sans-serif)",
              fontSize: "14px", fontWeight: 700, letterSpacing: "-0.03em",
              color: "var(--text)",
            }}>
              Cortex
            </span>
          </Link>

          {/* Desktop nav */}
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
                    borderRadius: "16px",
                    fontSize: "14px", fontWeight: isActive ? 700 : 450,
                    letterSpacing: "0.3px",
                    color: isActive ? "#0F1923" : "rgba(60,54,48,0.60)",
                    textDecoration: "none",
                    whiteSpace: "nowrap",
                    fontFamily: "var(--font-sans,'Inter',system-ui,sans-serif)",
                    transition: "color 0.2s ease, font-weight 0.2s ease",
                    zIndex: 2,
                  }}
                >
                  {isActive && !prefersReduced && (
                    <motion.span
                      layoutId="nav-active-pill"
                      style={{
                        position: "absolute", inset: 0,
                        borderRadius: "16px",
                        background: "rgba(30,42,56,0.12)",
                        border: "1px solid rgba(30,42,56,0.20)",
                        boxShadow: "inset 0 1px 0 rgba(255,255,255,0.60)",
                        zIndex: -1,
                      }}
                      transition={SPRING.gentle}
                      aria-hidden
                    />
                  )}
                  {isActive && prefersReduced && (
                    <span
                      style={{
                        position: "absolute", inset: 0,
                        borderRadius: "16px",
                        background: "rgba(30,42,56,0.12)",
                        border: "1px solid rgba(30,42,56,0.20)",
                        boxShadow: "inset 0 1px 0 rgba(255,255,255,0.60)",
                        zIndex: -1,
                      }}
                      aria-hidden
                    />
                  )}
                  {/* Active dot under label */}
                  {isActive && (
                    <motion.span
                      layoutId="nav-active-dot"
                      style={{
                        position: "absolute", bottom: 4, left: "50%",
                        translateX: "-50%",
                        width: 5, height: 5, borderRadius: "50%",
                        background: "#1E2A38",
                        zIndex: 2,
                      }}
                      transition={SPRING.gentle}
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
          }} />

          {/* CTA */}
          <motion.div
            style={{ position: "relative", zIndex: 3, marginLeft: "4px" }}
            whileHover={prefersReduced ? {} : CTA_HOVER}
            whileTap={prefersReduced ? {} : CTA_TAP}
            className="hidden md:block"
          >
            <DashboardLink
              style={{
                display: "inline-flex", alignItems: "center", justifyContent: "center",
                padding: "8px 18px", borderRadius: "18px",
                background: "#1E2A38",
                color: "#FFFFFF",
                fontSize: "13px", fontWeight: 600,
                textDecoration: "none", letterSpacing: "-0.01em",
                border: "1px solid rgba(255,255,255,0.10)",
                boxShadow:
                  "0 2px 12px rgba(0,0,0,0.22)," +
                  "inset 0 1px 4px rgba(255,255,255,0.08)",
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
              background: "rgba(255,255,255,0.20)",
              border: `0.5px solid rgba(255,255,255,0.40)`,
              cursor: "pointer", color: glass.iconColor,
              zIndex: 3, position: "relative", flexShrink: 0,
              boxShadow: "inset 0 1px 3px rgba(255,255,255,0.45)",
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

      <style dangerouslySetInnerHTML={{ __html: `nav:hover .liquid-glare { opacity: 1 !important; }` }} />

      {/* Mobile overlay */}
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
              background: "rgba(240,238,235,0.92)",
              backdropFilter: "blur(50px) saturate(200%) brightness(1.06)",
              WebkitBackdropFilter: "blur(50px) saturate(200%) brightness(1.06)",
              borderBottom: "0.5px solid rgba(255,255,255,0.55)",
            }}
          >
            <div className="flex items-center justify-between px-5 pt-5 pb-3">
              <span style={{
                fontFamily: "var(--font-display,'Syne',sans-serif)",
                fontSize: "16px", fontWeight: 700, letterSpacing: "-0.03em",
                color: "var(--text)",
              }}>
                Cortex
              </span>
              <motion.button
                onClick={() => setMobileOpen(false)}
                aria-label="Close navigation menu"
                whileTap={prefersReduced ? {} : { scale: 0.88 }}
                style={{
                  width: 32, height: 32, borderRadius: "50%",
                  background: "rgba(255,255,255,0.35)",
                  border: `0.5px solid rgba(255,255,255,0.55)`,
                  display: "flex", alignItems: "center", justifyContent: "center",
                  cursor: "pointer",
                  boxShadow: "inset 0 1px 3px rgba(255,255,255,0.65)",
                }}
              >
                <X style={{ width: 13, height: 13, color: "var(--text)" }} />
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
                        padding: "13px 16px", borderRadius: "16px",
                        fontSize: "16px", fontWeight: isActive ? 600 : 400,
                        color: isActive ? "var(--primary)" : "var(--text-secondary)",
                        background: isActive ? "rgba(255,255,255,0.40)" : "transparent",
                        border: `0.5px solid ${isActive ? "rgba(255,255,255,0.60)" : "rgba(255,255,255,0.35)"}`,
                        fontFamily: "var(--font-sans,'Inter',sans-serif)",
                        textDecoration: "none",
                        transition: "all 0.2s ease",
                        boxShadow: isActive
                          ? "inset 0 1px 4px rgba(255,255,255,0.70)"
                          : "none",
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
                    fontSize: "15px", fontWeight: 600, borderRadius: "16px",
                    background: "#1E2A38",
                    color: "#FFFFFF",
                    textDecoration: "none",
                    border: "1px solid rgba(255,255,255,0.10)",
                    boxShadow: "0 4px 16px rgba(0,0,0,0.20)",
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
