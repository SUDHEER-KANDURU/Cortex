"use client"

import type React from "react"
import { useState, useEffect } from "react"
import Link from "next/link"
import { Menu, X } from "lucide-react"

const navItems = [
  { href: "#works",        label: "Capabilities",  id: "works"        },
  { href: "#about",        label: "About",          id: "about"        },
  { href: "#testimonials", label: "What users say", id: "testimonials" },
  { href: "#awards",       label: "Tech & Stack",   id: "awards"       },
  { href: "#insights",     label: "Insights",       id: "insights"     },
]

export function PortfolioHeader() {
  const [scrollY,         setScrollY]         = useState(0)
  const [isMobileMenuOpen, setMobileOpen]     = useState(false)
  const [activeSection,   setActiveSection]   = useState<string>("")

  useEffect(() => {
    const onScroll = () => setScrollY(window.scrollY)
    window.addEventListener("scroll", onScroll, { passive: true })

    // Active section via IntersectionObserver
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

  // Three header states:
  // 0-20px   → always-visible solid white (at very top of page)
  // 20-80px  → liquid glass transitioning in
  // 80px+    → full liquid glass
  const glassOpacity = Math.min(1, Math.max(0, (scrollY - 20) / 60))

  return (
    <>
      <header
        className="fixed top-0 left-0 right-0 z-[200] transition-shadow duration-300"
        style={{
          isolation: "isolate",
          background: `rgba(255,255,255,${0.75 + glassOpacity * 0.15})`,
          backdropFilter: `blur(${8 + glassOpacity * 4}px) saturate(${140 + glassOpacity * 40}%)`,
          WebkitBackdropFilter: `blur(${8 + glassOpacity * 4}px) saturate(${140 + glassOpacity * 40}%)`,
          borderBottom: `1px solid rgba(255,255,255,${0.4 + glassOpacity * 0.5})`,
          boxShadow: glassOpacity > 0.5
            ? `0 1px 0 rgba(0,0,0,0.05), 0 4px 16px rgba(0,0,0,${0.03 * glassOpacity})`
            : "none",
        }}
      >
        <div className="max-w-[1280px] mx-auto px-6 md:px-12">
          <nav className="flex items-center justify-between h-16 md:h-20">

            {/* Logo */}
            <Link
              href="#"
              onClick={(e) => {
                e.preventDefault()
                setActiveSection("")
                window.scrollTo({ top: 0, behavior: "smooth" })
              }}
              style={{
                fontFamily: "var(--font-display,'Syne',sans-serif)",
                fontSize: "18px", fontWeight: 700,
                letterSpacing: "-0.03em", color: "#0a0a0a",
                textDecoration: "none",
              }}>
              Cortex
            </Link>

            {/* Desktop nav */}
            <div className="hidden md:flex items-center gap-1">
              {navItems.map((item) => {
                const isActive = activeSection === item.id
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={(e) => handleNavClick(e, item.href, item.id)}
                    className="relative px-4 py-2 rounded-full text-sm transition-all duration-250"
                    style={{
                      color: isActive ? "#0a0a0a" : "rgba(0,0,0,0.5)",
                      fontWeight: isActive ? 600 : 400,
                      background: isActive
                        ? "rgba(255,255,255,0.75)"
                        : "transparent",
                      backdropFilter: isActive ? "blur(8px) saturate(200%)" : "none",
                      WebkitBackdropFilter: isActive ? "blur(8px) saturate(200%)" : "none",
                      border: isActive
                        ? "1px solid rgba(255,255,255,0.9)"
                        : "1px solid transparent",
                      boxShadow: isActive
                        ? "0 2px 12px rgba(0,0,0,0.06), inset 0 1px 0 rgba(255,255,255,1)"
                        : "none",
                      textDecoration: "none",
                      transition: "color 0.2s ease, background 0.2s ease, box-shadow 0.2s ease",
                    }}
                    onMouseEnter={e => {
                      if (!isActive) {
                        e.currentTarget.style.color = "#0a0a0a"
                        e.currentTarget.style.background = "rgba(0,0,0,0.04)"
                      }
                    }}
                    onMouseLeave={e => {
                      if (!isActive) {
                        e.currentTarget.style.color = "rgba(0,0,0,0.5)"
                        e.currentTarget.style.background = "transparent"
                      }
                    }}
                  >
                    {item.label}
                    {isActive && (
                      <span style={{
                        position: "absolute", bottom: "4px", left: "50%",
                        transform: "translateX(-50%)",
                        width: "4px", height: "4px", borderRadius: "50%",
                        background: "#0a0a0a", display: "block",
                      }} />
                    )}
                  </Link>
                )
              })}
            </div>

            {/* CTA button — liquid glass outline on default, solid on hover */}
            <div className="hidden md:block">
              <Link
                href="/dashboard"
                className="inline-flex items-center justify-center px-5 py-2.5 text-sm font-semibold rounded-full transition-all duration-250"
                style={{
                  background: "#0a0a0a",
                  color: "#fff",
                  boxShadow: "0 2px 12px rgba(0,0,0,0.18)",
                  textDecoration: "none",
                }}
                onMouseEnter={e => {
                  const el = e.currentTarget as HTMLElement
                  el.style.background = "#000"
                  el.style.boxShadow = "0 6px 24px rgba(0,0,0,0.28)"
                  el.style.transform = "translateY(-1px)"
                }}
                onMouseLeave={e => {
                  const el = e.currentTarget as HTMLElement
                  el.style.background = "#0a0a0a"
                  el.style.boxShadow = "0 2px 12px rgba(0,0,0,0.18)"
                  el.style.transform = "none"
                }}>
                Launch App
              </Link>
            </div>

            {/* Mobile burger */}
            <button
              onClick={() => setMobileOpen(true)}
              className="md:hidden p-2 -mr-2"
              aria-label="Open menu"
              style={{ color: "#0a0a0a" }}>
              <Menu className="w-5 h-5" />
            </button>
          </nav>
        </div>
      </header>

      {/* Mobile overlay — liquid glass */}
      {isMobileMenuOpen && (
        <div
          className="fixed inset-0 z-[200] md:hidden"
          style={{
            background: "rgba(255,255,255,0.92)",
            backdropFilter: "blur(14px) saturate(200%)",
            WebkitBackdropFilter: "blur(14px) saturate(200%)",
          }}>
          <div className="flex flex-col h-full p-6">
            <div className="flex items-center justify-between h-16">
              <span style={{
                fontFamily: "var(--font-display,'Syne',sans-serif)",
                fontSize: "18px", fontWeight: 700,
                letterSpacing: "-0.03em", color: "#0a0a0a",
              }}>
                Cortex
              </span>
              <button
                onClick={() => setMobileOpen(false)}
                className="p-2 -mr-2"
                aria-label="Close menu">
                <X className="w-5 h-5" style={{ color: "#0a0a0a" }} />
              </button>
            </div>

            <nav className="flex flex-col gap-1 mt-8">
              {navItems.map((item) => {
                const isActive = activeSection === item.id
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={(e) => handleNavClick(e, item.href, item.id)}
                    style={{
                      display: "block",
                      padding: "14px 16px",
                      borderRadius: "14px",
                      fontSize: "22px",
                      fontWeight: isActive ? 700 : 500,
                      color: isActive ? "#0a0a0a" : "rgba(0,0,0,0.4)",
                      background: isActive
                        ? "rgba(255,255,255,0.8)"
                        : "transparent",
                      backdropFilter: isActive ? "blur(12px)" : "none",
                      WebkitBackdropFilter: isActive ? "blur(12px)" : "none",
                      border: isActive
                        ? "1px solid rgba(255,255,255,0.9)"
                        : "1px solid transparent",
                      fontFamily: "var(--font-display,'Syne',sans-serif)",
                      textDecoration: "none",
                      transition: "all 0.25s ease",
                    }}>
                    {item.label}
                  </Link>
                )
              })}
            </nav>

            <div className="mt-auto pb-4">
              <Link
                href="/dashboard"
                onClick={() => setMobileOpen(false)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  width: "100%",
                  padding: "16px",
                  fontSize: "16px",
                  fontWeight: 600,
                  borderRadius: "16px",
                  background: "#0a0a0a",
                  color: "#fff",
                  textDecoration: "none",
                  boxShadow: "0 4px 20px rgba(0,0,0,0.2)",
                }}>
                Launch App
              </Link>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
