"use client"

import Link from "next/link"
import { Github, Linkedin, Twitter } from "lucide-react"

const socialLinks = [
  { href: "https://github.com/SUDHEER-KANDURU/cortex", icon: Github,   label: "GitHub"   },
  { href: "#",                                          icon: Twitter,  label: "Twitter"  },
  { href: "#",                                          icon: Linkedin, label: "LinkedIn" },
]

const footerLinks = [
  { href: "https://github.com/SUDHEER-KANDURU/cortex", label: "GitHub",        external: true  },
  { href: "/docs",                                      label: "Documentation", external: false },
  { href: "/api",                                       label: "API",           external: false },
  { href: "/roadmap",                                   label: "Roadmap",       external: false },
  { href: "/contact",                                   label: "Contact",       external: false },
]

const VERSION = "v0.1.0"

export function PortfolioFooter() {
  return (
    <footer style={{
      borderTop: "1px solid rgba(255,255,255,0.7)",
      background: "rgba(255,255,255,0.6)",
      backdropFilter: "blur(10px) saturate(180%)",
      WebkitBackdropFilter: "blur(10px) saturate(180%)",
      boxShadow: "inset 0 1px 0 rgba(255,255,255,0.9)",
    }}>
      <div className="max-w-[1280px] mx-auto px-6 md:px-12 py-16 md:py-24">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-12 md:gap-8">

          {/* Brand */}
          <div className="md:col-span-2" data-reveal="up">
            <div
              className="logo-cube"
              style={{ width: 20, height: 20, background: '#111', borderRadius: 4,
                animation: 'logo-cube-rotate 120s linear infinite',
                marginBottom: 8 }}
            />
            <Link href="/"
              style={{
                fontFamily: "var(--font-display,'Syne',sans-serif)",
                fontSize: "22px", fontWeight: 700,
                letterSpacing: "-0.03em", color: "#0a0a0a",
                textDecoration: "none",
              }}>
              Cortex
            </Link>
            <p className="mt-4 text-sm leading-relaxed"
              style={{ color: "rgba(0,0,0,0.45)", maxWidth: "280px", lineHeight: 1.7 }}>
              Engineering Reasoning Engine — understand any codebase, generate architecture diagrams, learning paths, and interview prep. Fully offline.
            </p>

            {/* Social links — glass pills */}
            <div className="flex items-center gap-3 mt-6">
              {socialLinks.map((s) => (
                <Link key={s.label} href={s.href}
                  target="_blank" rel="noopener noreferrer"
                  className="p-2.5 rounded-full transition-all duration-250"
                  style={{
                    background: "rgba(255,255,255,0.7)",
                    backdropFilter: "blur(12px) saturate(180%)",
                    WebkitBackdropFilter: "blur(12px) saturate(180%)",
                    border: "1px solid rgba(255,255,255,0.9)",
                    boxShadow: "0 2px 8px rgba(0,0,0,0.06), inset 0 1px 0 rgba(255,255,255,1)",
                  }}
                  onMouseEnter={e => {
                    const el = e.currentTarget as HTMLElement
                    el.style.background = "#0a0a0a"
                    el.style.borderColor = "#0a0a0a"
                    el.style.transform = "translateY(-2px)"
                    el.style.boxShadow = "0 6px 20px rgba(0,0,0,0.15)"
                    const icon = el.querySelector("svg")
                    if (icon) (icon as SVGElement).style.color = "#fff"
                  }}
                  onMouseLeave={e => {
                    const el = e.currentTarget as HTMLElement
                    el.style.background = "rgba(255,255,255,0.7)"
                    el.style.borderColor = "rgba(255,255,255,0.9)"
                    el.style.transform = "none"
                    el.style.boxShadow = "0 2px 8px rgba(0,0,0,0.06), inset 0 1px 0 rgba(255,255,255,1)"
                    const icon = el.querySelector("svg")
                    if (icon) (icon as SVGElement).style.color = "#555"
                  }}
                  aria-label={s.label}>
                  <s.icon className="w-4 h-4" style={{ color: "#555", transition: "color 0.2s ease" }} />
                </Link>
              ))}
            </div>

            <div className="mt-5">
              <Link href="https://github.com/SUDHEER-KANDURU/cortex"
                target="_blank" rel="noopener noreferrer"
                className="footer-link"
                style={{
                  fontSize: "12px", color: "rgba(0,0,0,0.4)",
                  fontFamily: "var(--font-mono,'Fira Code',monospace)",
                  textDecoration: "none", transition: "color 0.2s ease",
                }}
                onMouseEnter={e => (e.currentTarget.style.color = "#111")}
                onMouseLeave={e => (e.currentTarget.style.color = "rgba(0,0,0,0.4)")}>
                github.com/SUDHEER-KANDURU/cortex
              </Link>
            </div>
          </div>

          {/* Links */}
          <div data-reveal="up" style={{ transitionDelay: "80ms" }}>
            <h4 style={{ fontSize: "12px", fontWeight: 700, color: "#111", marginBottom: "18px", letterSpacing: "0.08em", textTransform: "uppercase", fontFamily: "var(--font-mono,'Fira Code',monospace)" }}>
              Links
            </h4>
            <ul className="space-y-3">
              {footerLinks.map((link) => (
                <li key={link.label}>
                  <Link href={link.href}
                    {...(link.external ? { target: "_blank", rel: "noopener noreferrer" } : {})}
                    className="footer-link"
                    style={{ fontSize: "14px", color: "rgba(0,0,0,0.45)", textDecoration: "none", transition: "color 0.2s ease" }}
                    onMouseEnter={e => (e.currentTarget.style.color = "#111")}
                    onMouseLeave={e => (e.currentTarget.style.color = "rgba(0,0,0,0.45)")}>
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Star CTA */}
          <div data-reveal="up" style={{ transitionDelay: "160ms" }}>
            <h4 style={{ fontSize: "12px", fontWeight: 700, color: "#111", marginBottom: "18px", letterSpacing: "0.08em", textTransform: "uppercase", fontFamily: "var(--font-mono,'Fira Code',monospace)" }}>
              Stay Updated
            </h4>
            <p style={{ fontSize: "14px", color: "rgba(0,0,0,0.45)", marginBottom: "18px", lineHeight: 1.6 }}>
              Star the repo to follow Cortex development.
            </p>
            <Link href="https://github.com/SUDHEER-KANDURU/cortex"
              target="_blank" rel="noopener noreferrer"
              className="cta-shimmer inline-flex items-center justify-center w-full px-4 py-3 text-sm font-semibold text-white rounded-xl transition-all duration-300"
              style={{
                background: "#0a0a0a",
                boxShadow: "0 4px 16px rgba(0,0,0,0.2)",
                textDecoration: "none",
              }}
              onMouseEnter={e => {
                const el = e.currentTarget as HTMLElement
                el.style.background = "#000"
                el.style.boxShadow = "0 8px 28px rgba(0,0,0,0.3)"
                el.style.transform = "translateY(-2px)"
              }}
              onMouseLeave={e => {
                const el = e.currentTarget as HTMLElement
                el.style.background = "#0a0a0a"
                el.style.boxShadow = "0 4px 16px rgba(0,0,0,0.2)"
                el.style.transform = "none"
              }}>
              ★&nbsp; Star on GitHub
            </Link>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="flex flex-col md:flex-row items-center justify-between gap-4 mt-16 pt-8"
          style={{ borderTop: "1px solid rgba(0,0,0,0.07)" }}>
          <p style={{ fontSize: "12px", color: "rgba(0,0,0,0.3)", fontFamily: "var(--font-mono,'Fira Code',monospace)" }}>
            © {new Date().getFullYear()} Cortex — Built by Sudheer Kanduru
          </p>
          <span style={{ fontSize: "12px", color: "rgba(0,0,0,0.3)", fontFamily: "var(--font-mono,'Fira Code',monospace)" }}>
            {VERSION}
          </span>
          <Link href="https://github.com/SUDHEER-KANDURU/cortex"
            target="_blank" rel="noopener noreferrer"
            className="footer-link"
            style={{ fontSize: "12px", color: "rgba(0,0,0,0.3)", textDecoration: "none", fontFamily: "var(--font-mono,'Fira Code',monospace)", transition: "color 0.2s ease" }}
            onMouseEnter={e => (e.currentTarget.style.color = "#111")}
            onMouseLeave={e => (e.currentTarget.style.color = "rgba(0,0,0,0.3)")}>
            MIT License
          </Link>
        </div>
      </div>
    </footer>
  )
}
