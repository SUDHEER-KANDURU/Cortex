"use client"

import Link from "next/link"
import { ArrowUpRight, Github } from "lucide-react"
import { DashboardLink } from "@/components/shared/DashboardLink"

export function PortfolioFinalCTA() {
  return (
    <section id="contact" className="py-24 md:py-36 relative overflow-hidden"
      style={{ borderTop: "1px solid var(--cx-card-border)", background: "var(--cx-section-bg)", backdropFilter: "blur(20px) saturate(200%)", WebkitBackdropFilter: "blur(20px) saturate(200%)" }}>

      {/* Floating orbs */}
      <div style={{ position: "absolute", top: "-10%", left: "5%", width: "400px", height: "400px", borderRadius: "50%", background: "radial-gradient(circle, rgba(0,0,0,0.025) 0%, transparent 70%)", filter: "blur(60px)", animation: "orb-drift 18s ease-in-out infinite", pointerEvents: "none" }} />
      <div style={{ position: "absolute", bottom: "-5%", right: "8%", width: "300px", height: "300px", borderRadius: "50%", background: "radial-gradient(circle, rgba(0,0,0,0.02) 0%, transparent 70%)", filter: "blur(48px)", animation: "orb-drift 22s ease-in-out infinite reverse", pointerEvents: "none" }} />

      <div className="max-w-[1280px] mx-auto px-6 md:px-12 relative z-10">
        <div className="max-w-3xl mx-auto text-center">

          {/* Eyebrow */}
          <div className="cx-pill inline-flex items-center gap-2 mb-6 px-4 py-2 rounded-full"
            style={{ backdropFilter: "blur(8px) saturate(180%)", WebkitBackdropFilter: "blur(8px) saturate(180%)" }}>
            <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--cx-text)", display: "inline-block", animation: "pulse-dot 2s ease-in-out infinite" }} />
            <span className="cx-text-mono" style={{ fontSize: "11px", fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase", fontFamily: "var(--font-mono,'JetBrains Mono',monospace)" }}>
              Free &amp; Offline
            </span>
          </div>

          <h2 className="cx-text text-[42px] md:text-[56px] lg:text-[72px] font-semibold tracking-tight text-balance"
            style={{ fontFamily: "var(--font-sans,'Geist',system-ui,sans-serif)", letterSpacing: "-0.045em", lineHeight: 1.04 }}>
            Have a codebase?<br />
            <span style={{ opacity: 0.45 }}>Let Cortex map it.</span>
          </h2>

          <p className="cx-text-muted mt-6 text-base leading-[1.7] max-w-[480px] mx-auto">
            Paste a GitHub URL and get architecture diagrams, learning paths, and interview prep in seconds. No signup. No API keys. No cloud.
          </p>

          {/* Pipeline badges */}
          <div className="flex flex-wrap items-center justify-center gap-2 mt-10">
            {["Scan Repo", "Parse AST", "Build Graph", "Generate Artifacts"].map((step, i) => (
              <div key={step} className="flex items-center gap-2">
                <span className="cx-pill cx-text-mono" style={{ padding: "6px 16px", borderRadius: "100px", fontSize: "11px", fontWeight: 600, backdropFilter: "blur(8px) saturate(180%)", WebkitBackdropFilter: "blur(8px) saturate(180%)", letterSpacing: "0.04em", fontFamily: "var(--font-mono,'JetBrains Mono',monospace)", transition: "all 0.25s ease" }}
                  onMouseEnter={e => { (e.currentTarget as HTMLElement).style.transform = "translateY(-2px)" }}
                  onMouseLeave={e => { (e.currentTarget as HTMLElement).style.transform = "none" }}>
                  {step}
                </span>
                {i < 3 && <span className="cx-text-faint" style={{ fontSize: "14px", fontWeight: 300 }}>→</span>}
              </div>
            ))}
          </div>

          {/* CTAs */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mt-10">
            <DashboardLink
              className="group inline-flex items-center justify-center gap-2 px-9 py-4 text-base font-semibold rounded-full"
              style={{
                background: "linear-gradient(135deg, var(--primary) 0%, #00c9a7 100%)",
                color: "#060810",
                boxShadow: "0 8px 32px var(--primary-glow), inset 0 1px 0 rgba(255,255,255,0.22)",
                transition: "transform 0.3s cubic-bezier(0.16,1,0.3,1), box-shadow 0.3s ease, filter 0.2s ease",
              }}
              onMouseEnter={e => { const el = e.currentTarget as HTMLAnchorElement; el.style.filter = "brightness(1.1)"; el.style.boxShadow = "0 16px 48px var(--primary-glow), inset 0 1px 0 rgba(255,255,255,0.22)" }}
              onMouseLeave={e => { const el = e.currentTarget as HTMLAnchorElement; el.style.filter = ""; el.style.boxShadow = "0 8px 32px var(--primary-glow), inset 0 1px 0 rgba(255,255,255,0.22)" }}>
              Analyze a Repository
              <ArrowUpRight className="w-4 h-4 transition-transform duration-300 group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
            </DashboardLink>

            <Link href="https://github.com/SUDHEER-KANDURU/cortex" target="_blank" rel="noopener noreferrer"
              className="cx-row cx-link inline-flex items-center justify-center gap-2 px-8 py-4 text-base font-medium rounded-full"
              style={{ backdropFilter: "blur(12px) saturate(200%)", WebkitBackdropFilter: "blur(12px) saturate(200%)", transition: "transform 0.3s cubic-bezier(0.16,1,0.3,1), box-shadow 0.3s ease" }}
              onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = "var(--cx-pill-bg)" }}
              onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = "" }}>
              <Github className="w-4 h-4" />
              Star on GitHub
            </Link>
          </div>

          <p className="cx-text-faint mt-8 text-xs" style={{ fontFamily: "var(--font-mono,'JetBrains Mono',monospace)", letterSpacing: "0.06em" }}>
            MIT License · Built at SRMIST Chennai · Zero cloud dependencies
          </p>
        </div>
      </div>
    </section>
  )
}

