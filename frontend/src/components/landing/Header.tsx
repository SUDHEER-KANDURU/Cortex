"use client"

import type React from "react"
import { useState, useEffect } from "react"
import Link from "next/link"
import { X, Zap, Layers, Users, Cpu, BookOpen, LayoutDashboard } from "lucide-react"

const navItems = [
  { href: "#works",        label: "Capabilities", id: "works",        Icon: Layers   },
  { href: "#about",        label: "About",         id: "about",        Icon: Users    },
  { href: "#testimonials", label: "Reviews",       id: "testimonials", Icon: Zap      },
  { href: "#awards",       label: "Stack",         id: "awards",       Icon: Cpu      },
  { href: "#insights",     label: "Insights",      id: "insights",     Icon: BookOpen },
]

export function PortfolioHeader() {
  const [isMobileMenuOpen, setMobileOpen] = useState(false)
  const [activeSection, setActiveSection] = useState<string>("")
  const [scrolled, setScrolled] = useState(false)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 10)
    window.addEventListener("scroll", onScroll, { passive: true })

    const observers: IntersectionObserver[] = []
    navItems.forEach(({ id }) => {
      const el = document.getElementById(id)
      if (!el) return
      const obs = new IntersectionObserver(
        ([entry]) => { if (entry.isIntersecting) setActiveSection(id) },
        { threshold: 0.15, rootMargin: "-80px 0px -40% 0px" },
      )
      obs.observe(el)
      observers.push(obs)
    })

    return () => {
      window.removeEventListener("scroll", onScroll)
      observers.forEach(o => o.disconnect())
    }
  }, [])

  const handleNavClick = (e: React.MouseEvent<HTMLAnchorElement>, href: string, id: string) => {
    e.preventDefault()
    setActiveSection(id)
    const el = document.querySelector(href)
    if (el) {
      const offset = el.getBoundingClientRect().top + window.pageYOffset - 80
      window.scrollTo({ top: offset, behavior: "smooth" })
    }
    setMobileOpen(false)
  }

  const pillStyle: React.CSSProperties = {
    marginTop: "12px",
    pointerEvents: "auto",
    background: scrolled ? "rgba(255,255,255,0.82)" : "rgba(255,255,255,0.68)",
    backdropFilter: "saturate(180%) blur(20px)",
    WebkitBackdropFilter: "saturate(180%) blur(20px)",
    border: "1px solid rgba(255,255,255,0.9)",
    borderBottom: "1px solid rgba(0,0,0,0.06)",
    borderRadius: "100px",
    boxShadow: scrolled
      ? "0 2px 20px rgba(0,0,0,0.10), 0 1px 4px rgba(0,0,0,0.06)"
      : "0 1px 12px rgba(0,0,0,0.07)",
    padding: "5px",
    display: "flex",
    alignItems: "center",
    gap: "2px",
    transition: "background 0.4s ease, box-shadow 0.4s ease",
  }

  return (
    <>
      <header
        className="fixed top-0 left-0 right-0 z-[200] flex justify-center"
        style={{ pointerEvents: "none" }}
      >
        <div style={pillStyle}>
          {/* Logo */}
          <Link
            href="#"
            onClick={e => {
              e.preventDefault()
              setActiveSection("")
              window.scrollTo({ top: 0, behavior: "smooth" })
            }}
            style={{
              display: "flex", alignItems: "center", gap: "7px",
              padding: "7px 14px 7px 8px",
              borderRadius: "100px",
              background: "rgba(0,0,0,0.04)",
              border: "1px solid rgba(0,0,0,0.05)",
              textDecoration: "none",
              transition: "background 0.2s ease",
            }}
            onMouseEnter={e => (e.currentTarget.style.background = "rgba(0,0,0,0.07)")}
            onMouseLeave={e => (e.currentTarget.style.background = "rgba(0,0,0,0.04)")}
          >
            <span style={{
              width: 24, height: 24, borderRadius: "7px",
              background: "#0a0a0a",
              display: "inline-flex", alignItems: "center", justifyContent: "center",
              flexShrink: 0,
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

          {/* Divider */}
          <div style={{ width: 1, height: 18, background: "rgba(0,0,0,0.1)", margin: "0 3px", flexShrink: 0 }} />

          {/* Desktop nav */}
          <div className="hidden md:flex items-center gap-0.5">
            {navItems.map(({ href, label, id, Icon }) => {
              const isActive = activeSection === id
              return (
                <Link
                  key={href}
                  href={href}
                  onClick={e => handleNavClick(e, href, id)}
                  style={{
                    display: "flex", alignItems: "center",
                    gap: isActive ? "6px" : "0",
                    padding: isActive ? "7px 13px 7px 10px" : "7px 11px",
                    borderRadius: "100px",
                    background: isActive ? "#0a0a0a" : "transparent",
                    boxShadow: isActive
                      ? "0 1px 6px rgba(0,0,0,0.18), inset 0 1px 0 rgba(255,255,255,0.1)"
                      : "none",
                    textDecoration: "none",
                    transition: "all 0.3s cubic-bezier(0.16,1,0.3,1)",
                    overflow: "hidden",
                    whiteSpace: "nowrap",
                    minWidth: isActive ? undefined : "36px",
                    justifyContent: "center",
                  }}
                  onMouseEnter={e => {
                    if (!isActive) e.currentTarget.style.background = "rgba(0,0,0,0.05)"
                  }}
                  onMouseLeave={e => {
                    if (!isActive) e.currentTarget.style.background = "transparent"
                  }}
                >
                  <Icon style={{
                    width: 14, height: 14, flexShrink: 0,
                    color: isActive ? "#fff" : "rgba(0,0,0,0.4)",
                    transition: "color 0.2s ease",
                  }} />
                  {isActive && (
                    <span style={{
                      fontSize: "13px", fontWeight: 600,
                      color: "#fff",
                      fontFamily: "var(--font-sans,'DM Sans',sans-serif)",
                    }}>
                      {label}
                    </span>
                  )}
                </Link>
              )
            })}
          </div>

          {/* Divider */}
          <div className="hidden md:block" style={{ width: 1, height: 18, background: "rgba(0,0,0,0.1)", margin: "0 3px", flexShrink: 0 }} />

          {/* CTA */}
          <Link
            href="/dashboard"
            data-magnetic
            data-magnetic-dark
            className="hidden md:inline-flex items-center justify-center"
            style={{
              padding: "7px 15px",
              borderRadius: "100px",
              background: "#0a0a0a",
              color: "#fff",
              fontSize: "13px",
              fontWeight: 600,
              textDecoration: "none",
              boxShadow: "0 1px 8px rgba(0,0,0,0.2), inset 0 1px 0 rgba(255,255,255,0.08)",
              whiteSpace: "nowrap",
              transition: "box-shadow 0.2s ease",
            }}
            onMouseEnter={e => {
              e.currentTarget.style.boxShadow = "0 3px 14px rgba(0,0,0,0.32), inset 0 1px 0 rgba(255,255,255,0.08)"
            }}
            onMouseLeave={e => {
              e.currentTarget.style.boxShadow = "0 1px 8px rgba(0,0,0,0.2), inset 0 1px 0 rgba(255,255,255,0.08)"
            }}
          >
            Launch App
          </Link>

          {/* Mobile burger */}
          <button
            onClick={() => setMobileOpen(true)}
            className="md:hidden flex items-center justify-center"
            aria-label="Open menu"
            style={{
              width: 36, height: 36, borderRadius: "100px",
              background: "rgba(0,0,0,0.04)",
              border: "1px solid rgba(0,0,0,0.07)",
              cursor: "pointer", color: "#0a0a0a",
            }}
          >
            <svg width="14" height="11" viewBox="0 0 14 11" fill="none">
              <rect width="14" height="1.5" rx="0.75" fill="currentColor"/>
              <rect y="4.75" width="9" height="1.5" rx="0.75" fill="currentColor"/>
              <rect y="9.5" width="14" height="1.5" rx="0.75" fill="currentColor"/>
            </svg>
          </button>
        </div>
      </header>

      {/* Mobile overlay */}
      {isMobileMenuOpen && (
        <div
          className="fixed inset-0 z-[201] md:hidden flex flex-col"
          style={{
            background: "rgba(248,248,248,0.94)",
            backdropFilter: "saturate(180%) blur(24px)",
            WebkitBackdropFilter: "saturate(180%) blur(24px)",
          }}
        >
          <div className="flex items-center justify-between px-6 pt-5 pb-4">
            <span style={{
              fontFamily: "var(--font-display,'Syne',sans-serif)",
              fontSize: "17px", fontWeight: 700,
              letterSpacing: "-0.03em", color: "#0a0a0a",
            }}>Cortex</span>
            <button
              onClick={() => setMobileOpen(false)}
              style={{
                width: 32, height: 32, borderRadius: "50%",
                background: "rgba(0,0,0,0.07)",
                border: "1px solid rgba(0,0,0,0.08)",
                display: "flex", alignItems: "center", justifyContent: "center",
                cursor: "pointer",
              }}
              aria-label="Close menu"
            >
              <X style={{ width: 14, height: 14, color: "#0a0a0a" }} />
            </button>
          </div>

          <nav className="flex flex-col gap-1 px-4 flex-1">
            {navItems.map(({ href, label, id, Icon }) => {
              const isActive = activeSection === id
              return (
                <Link
                  key={href} href={href}
                  onClick={e => handleNavClick(e, href, id)}
                  style={{
                    display: "flex", alignItems: "center", gap: "12px",
                    padding: "13px 16px",
                    borderRadius: "14px",
                    fontSize: "17px", fontWeight: isActive ? 700 : 500,
                    color: isActive ? "#fff" : "rgba(0,0,0,0.55)",
                    background: isActive ? "#0a0a0a" : "rgba(0,0,0,0.03)",
                    border: `1px solid ${isActive ? "transparent" : "rgba(0,0,0,0.05)"}`,
                    fontFamily: "var(--font-display,'Syne',sans-serif)",
                    textDecoration: "none",
                    transition: "all 0.2s ease",
                  }}
                >
                  <Icon style={{ width: 17, height: 17, color: isActive ? "#fff" : "rgba(0,0,0,0.35)" }} />
                  {label}
                </Link>
              )
            })}
          </nav>

          <div className="px-4 pb-8 pt-4">
            <Link href="/dashboard" onClick={() => setMobileOpen(false)} style={{
              display: "flex", alignItems: "center", justifyContent: "center",
              width: "100%", padding: "15px",
              fontSize: "15px", fontWeight: 600,
              borderRadius: "14px",
              background: "#0a0a0a", color: "#fff",
              textDecoration: "none",
              boxShadow: "0 4px 20px rgba(0,0,0,0.18)",
            }}>
              Launch App
            </Link>
          </div>
        </div>
      )}
    </>
  )
}
