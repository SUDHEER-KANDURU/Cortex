"use client"

import type React from "react"
import { useState, useEffect } from "react"
import Link from "next/link"
import { Menu, X } from "lucide-react"

const navItems = [
  { href: "#works",        label: "Capabilities",     number: "01" },
  { href: "#about",        label: "About",             number: "02" },
  { href: "#testimonials", label: "What users say",    number: "03" },
  { href: "#awards",       label: "Tech & Stack",      number: "04" },
  { href: "#insights",     label: "Insights",          number: "05" },
]

function cn(...classes: (string | boolean | undefined)[]) {
  return classes.filter(Boolean).join(" ")
}

export function PortfolioHeader() {
  const [isScrolled, setIsScrolled]       = useState(false)
  const [isMobileMenuOpen, setMobileOpen] = useState(false)

  useEffect(() => {
    const fn = () => setIsScrolled(window.scrollY > 50)
    window.addEventListener("scroll", fn)
    return () => window.removeEventListener("scroll", fn)
  }, [])

  const handleNavClick = (e: React.MouseEvent<HTMLAnchorElement>, href: string) => {
    e.preventDefault()
    const el = document.querySelector(href)
    if (el) {
      const offset = el.getBoundingClientRect().top + window.pageYOffset - 80
      window.scrollTo({ top: offset, behavior: "smooth" })
    }
    setMobileOpen(false)
  }

  return (
    <>
      <header className={cn(
        "fixed top-0 left-0 right-0 z-50 transition-all duration-300",
        isScrolled ? "bg-background/80 backdrop-blur-md border-b border-border" : "bg-transparent",
      )}>
        <div className="max-w-[1280px] mx-auto px-6 md:px-12">
          <nav className="flex items-center justify-between h-16 md:h-20">
            <Link href="#" onClick={(e) => { e.preventDefault(); window.scrollTo({ top: 0, behavior: "smooth" }) }}
              className="text-lg font-semibold tracking-tight">
              Cortex
            </Link>

            <div className="hidden md:flex items-center gap-8">
              {navItems.map((item) => (
                <Link key={item.href} href={item.href}
                  onClick={(e) => handleNavClick(e, item.href)}
                  className="text-sm text-muted-foreground hover:text-foreground transition-colors">
                  {item.label}
                  <span className="text-xs ml-1 opacity-50">({item.number})</span>
                </Link>
              ))}
            </div>

            <div className="hidden md:block">
              <Link href="/dashboard"
                className="inline-flex items-center justify-center px-5 py-2.5 text-sm font-medium rounded-full text-white transition-all hover:shadow-xl relative overflow-hidden group"
                style={{ background: "linear-gradient(135deg, #203eec 0%, #00d4ff 100%)", boxShadow: "0 4px 20px rgba(32,62,236,0.3)" }}>
                <span className="relative z-10">Launch App</span>
                <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300 blur-xl bg-gradient-to-r from-[#203eec] to-[#00d4ff]" />
              </Link>
            </div>

            <button onClick={() => setMobileOpen(true)} className="md:hidden p-2 -mr-2" aria-label="Open menu">
              <Menu className="w-5 h-5" />
            </button>
          </nav>
        </div>
      </header>

      {isMobileMenuOpen && (
        <div className="fixed inset-0 z-50 bg-background md:hidden">
          <div className="flex flex-col h-full p-6">
            <div className="flex items-center justify-between">
              <span className="text-lg font-semibold tracking-tight">Cortex</span>
              <button onClick={() => setMobileOpen(false)} className="p-2 -mr-2" aria-label="Close menu">
                <X className="w-5 h-5" />
              </button>
            </div>
            <nav className="flex flex-col gap-6 mt-12">
              {navItems.map((item) => (
                <Link key={item.href} href={item.href}
                  onClick={(e) => handleNavClick(e, item.href)}
                  className="text-3xl font-semibold hover:text-muted-foreground transition-colors">
                  {item.label}
                </Link>
              ))}
            </nav>
            <div className="mt-auto">
              <Link href="/dashboard" onClick={() => setMobileOpen(false)}
                className="inline-flex items-center justify-center w-full px-5 py-3 text-base font-medium rounded-full text-white transition-all hover:shadow-xl relative overflow-hidden group"
                style={{ background: "linear-gradient(135deg, #203eec 0%, #00d4ff 100%)", boxShadow: "0 4px 20px rgba(32,62,236,0.3)" }}>
                <span className="relative z-10">Launch App</span>
                <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300 blur-xl bg-gradient-to-r from-[#203eec] to-[#00d4ff]" />
              </Link>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
