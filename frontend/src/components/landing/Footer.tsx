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
      borderTop: "1px solid var(--cx-card-border)",
      background: "rgba(255,255,255,0.06)",
      backdropFilter: "saturate(200%) blur(24px)",
      WebkitBackdropFilter: "saturate(200%) blur(24px)",
    }}>
      <div className="max-w-[1280px] mx-auto px-6 md:px-12 py-16 md:py-24">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-12 md:gap-8">

          {/* Brand */}
          <div className="md:col-span-2" data-reveal="up">
            <div style={{ width: 20, height: 20, background: 'var(--cx-text)', borderRadius: 4, animation: 'logo-cube-rotate 120s linear infinite', marginBottom: 8 }} />
            <Link href="/" className="cx-text" style={{ fontFamily: "var(--font-sans)", fontSize: "22px", fontWeight: 700, letterSpacing: "-0.03em", textDecoration: "none" }}>
              Cortex
            </Link>
            <p className="cx-text-muted mt-4 text-sm leading-relaxed" style={{ maxWidth: "280px", lineHeight: 1.7 }}>
              Engineering Reasoning Engine — understand any codebase, generate architecture diagrams, learning paths, and interview prep. Fully offline.
            </p>

            <div className="flex items-center gap-3 mt-6">
              {socialLinks.map((s) => (
                <Link key={s.label} href={s.href} target="_blank" rel="noopener noreferrer"
                  className="cx-stat-card p-2.5 rounded-full transition-all duration-200"
                  style={{ backdropFilter: "blur(12px) saturate(180%)", WebkitBackdropFilter: "blur(12px) saturate(180%)" }}
                  onMouseEnter={e => {
                    const el = e.currentTarget as HTMLElement
                    el.style.background = "var(--cx-text)"
                    const icon = el.querySelector("svg"); if (icon) (icon as SVGElement).style.color = "#fff"
                  }}
                  onMouseLeave={e => {
                    const el = e.currentTarget as HTMLElement
                    el.style.background = ""
                    const icon = el.querySelector("svg"); if (icon) (icon as SVGElement).style.color = ""
                  }}
                  aria-label={s.label}>
                  <s.icon className="cx-text-muted w-4 h-4 transition-colors duration-200" />
                </Link>
              ))}
            </div>

            <div className="mt-5">
              <Link href="https://github.com/SUDHEER-KANDURU/cortex" target="_blank" rel="noopener noreferrer"
                className="cx-text-faint footer-link"
                style={{ fontSize: "12px", fontFamily: "var(--font-mono)", textDecoration: "none", transition: "color 0.2s ease" }}>
                github.com/SUDHEER-KANDURU/cortex
              </Link>
            </div>
          </div>

          {/* Links */}
          <div data-reveal="up" style={{ transitionDelay: "80ms" }}>
            <h4 className="cx-text" style={{ fontSize: "12px", fontWeight: 700, marginBottom: "18px", letterSpacing: "0.08em", textTransform: "uppercase", fontFamily: "var(--font-mono)" }}>
              Links
            </h4>
            <ul className="space-y-3">
              {footerLinks.map((link) => (
                <li key={link.label}>
                  <Link href={link.href}
                    {...(link.external ? { target: "_blank", rel: "noopener noreferrer" } : {})}
                    className="cx-text-muted footer-link"
                    style={{ fontSize: "14px", textDecoration: "none", transition: "color 0.2s ease" }}>
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Star CTA */}
          <div data-reveal="up" style={{ transitionDelay: "160ms" }}>
            <h4 className="cx-text" style={{ fontSize: "12px", fontWeight: 700, marginBottom: "18px", letterSpacing: "0.08em", textTransform: "uppercase", fontFamily: "var(--font-mono)" }}>
              Stay Updated
            </h4>
            <p className="cx-text-muted" style={{ fontSize: "14px", marginBottom: "18px", lineHeight: 1.6 }}>
              Star the repo to follow Cortex development.
            </p>
            <Link href="https://github.com/SUDHEER-KANDURU/cortex" target="_blank" rel="noopener noreferrer"
              className="cta-shimmer inline-flex items-center justify-center w-full px-4 py-3 text-sm font-semibold rounded-xl transition-all duration-300"
              style={{
                background: "linear-gradient(135deg, var(--primary) 0%, #00c9a7 100%)",
                color: "#060810",
                boxShadow: "0 4px 16px var(--primary-glow)",
                textDecoration: "none",
              }}
              onMouseEnter={e => { const el = e.currentTarget as HTMLElement; el.style.filter = "brightness(1.1)" }}
              onMouseLeave={e => { const el = e.currentTarget as HTMLElement; el.style.filter = "" }}>
              ★&nbsp; Star on GitHub
            </Link>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="flex flex-col md:flex-row items-center justify-between gap-4 mt-16 pt-8 cx-divider" style={{ borderTop: "1px solid var(--cx-divider)" }}>
          <p className="cx-text-faint" style={{ fontSize: "12px", fontFamily: "var(--font-mono)" }}>
            © {new Date().getFullYear()} Cortex — Built by Sudheer Kanduru
          </p>
          <span className="cx-text-faint" style={{ fontSize: "12px", fontFamily: "var(--font-mono)" }}>{VERSION}</span>
          <Link href="https://github.com/SUDHEER-KANDURU/cortex" target="_blank" rel="noopener noreferrer"
            className="cx-text-faint footer-link"
            style={{ fontSize: "12px", textDecoration: "none", fontFamily: "var(--font-mono)", transition: "color 0.2s ease" }}>
            MIT License
          </Link>
        </div>
      </div>
    </footer>
  )
}

