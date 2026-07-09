"use client"

import Link from "next/link"
import { Github, Linkedin, Twitter } from "lucide-react"

const socialLinks = [
  { href: "https://github.com/SUDHEER-KANDURU/cortex", icon: Github,   label: "GitHub"   },
  { href: "#",                                          icon: Twitter,  label: "Twitter"  },
  { href: "#",                                          icon: Linkedin, label: "LinkedIn" },
]

const footerLinks = [
  { href: "/",          label: "Home"       },
  { href: "#about",     label: "About"      },
  { href: "#works",     label: "Capabilities" },
  { href: "#insights",  label: "Insights"   },
  { href: "/dashboard", label: "Dashboard"  },
]

export function PortfolioFooter() {
  return (
    <footer className="border-t border-border">
      <div className="max-w-[1280px] mx-auto px-6 md:px-12 py-16 md:py-24">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-12 md:gap-8">
          {/* Brand */}
          <div className="md:col-span-2">
            <Link href="/" className="text-xl font-semibold tracking-tight">Cortex</Link>
            <p className="mt-4 text-muted-foreground text-sm max-w-xs leading-relaxed">
              Engineering Reasoning Engine — understand any codebase, generate architecture diagrams, learning paths, and interview prep. Fully offline.
            </p>
            <div className="flex items-center gap-4 mt-6">
              {socialLinks.map((s) => (
                <Link key={s.label} href={s.href} target="_blank" rel="noopener noreferrer"
                  className="p-2 rounded-full bg-secondary transition-colors"
                  onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = "#203eec20")}
                  onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = "")}
                  aria-label={s.label}>
                  <s.icon className="w-4 h-4" style={{ color: "#203eec" }} />
                </Link>
              ))}
            </div>
            <div className="mt-4">
              <Link href="https://github.com/SUDHEER-KANDURU/cortex" target="_blank" rel="noopener noreferrer"
                className="text-sm transition-colors hover:underline" style={{ color: "#203eec" }}>
                github.com/SUDHEER-KANDURU/cortex
              </Link>
            </div>
          </div>

          {/* Pages */}
          <div>
            <h4 className="text-sm font-semibold mb-4">Pages</h4>
            <ul className="space-y-3">
              {footerLinks.map((link) => (
                <li key={link.label}>
                  <Link href={link.href} className="text-sm text-muted-foreground hover:text-foreground transition-colors">
                    {link.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Newsletter placeholder */}
          <div>
            <h4 className="text-sm font-semibold mb-4">Stay Updated</h4>
            <p className="text-sm text-muted-foreground mb-4">Star the repo to follow Cortex development.</p>
            <Link href="https://github.com/SUDHEER-KANDURU/cortex" target="_blank" rel="noopener noreferrer"
              className="inline-flex items-center justify-center w-full px-4 py-2.5 text-sm font-medium text-white rounded-lg transition-all"
              style={{ background: "linear-gradient(135deg, #203eec 0%, #00d4ff 100%)", boxShadow: "0 4px 20px rgba(32,62,236,0.3)" }}
              onMouseEnter={(e) => { e.currentTarget.style.boxShadow = "0 8px 30px rgba(32,62,236,0.5), 0 0 40px rgba(0,212,255,0.3)" }}
              onMouseLeave={(e) => { e.currentTarget.style.boxShadow = "0 4px 20px rgba(32,62,236,0.3)" }}>
              ★ Star on GitHub
            </Link>
          </div>
        </div>

        <div className="flex flex-col md:flex-row items-center justify-between gap-4 mt-16 pt-8 border-t border-border">
          <p className="text-xs text-muted-foreground">
            © {new Date().getFullYear()} Cortex — Built by Sudheer Kanduru · SRMIST, Chennai
          </p>
          <div className="flex items-center gap-6">
            <Link href="https://github.com/SUDHEER-KANDURU/cortex" target="_blank" rel="noopener noreferrer"
              className="text-xs text-muted-foreground hover:text-foreground transition-colors">
              MIT License
            </Link>
          </div>
        </div>
      </div>
    </footer>
  )
}
