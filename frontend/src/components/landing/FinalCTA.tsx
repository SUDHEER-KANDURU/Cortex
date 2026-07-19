"use client"

import Link from "next/link"
import { ArrowUpRight, Github } from "lucide-react"

export function PortfolioFinalCTA() {
  return (
    <section id="contact" className="py-24 md:py-36 relative overflow-hidden"
      style={{
        borderTop: "1px solid rgba(255,255,255,0.65)",
        background: "rgba(255,255,255,0.58)",
        backdropFilter: "blur(10px) saturate(180%)",
        WebkitBackdropFilter: "blur(10px) saturate(180%)",
        boxShadow: "inset 0 1px 0 rgba(255,255,255,0.95)",
      }}>

      {/* ── Floating orbs — ambient depth ── */}
      <div style={{
        position: "absolute", top: "-10%", left: "5%",
        width: "400px", height: "400px", borderRadius: "50%",
        background: "radial-gradient(circle, rgba(0,0,0,0.025) 0%, transparent 70%)",
        filter: "blur(60px)",
        animation: "orb-drift 18s ease-in-out infinite",
        pointerEvents: "none",
      }} />
      <div style={{
        position: "absolute", bottom: "-5%", right: "8%",
        width: "300px", height: "300px", borderRadius: "50%",
        background: "radial-gradient(circle, rgba(0,0,0,0.02) 0%, transparent 70%)",
        filter: "blur(48px)",
        animation: "orb-drift 22s ease-in-out infinite reverse",
        pointerEvents: "none",
      }} />

      {/* Subtle dot grid */}
      <div style={{
        position: "absolute", inset: 0, pointerEvents: "none",
        backgroundImage: "radial-gradient(rgba(0,0,0,0.08) 1px, transparent 1px)",
        backgroundSize: "28px 28px",
        maskImage: "radial-gradient(ellipse 70% 60% at 50% 50%, black 0%, transparent 100%)",
        WebkitMaskImage: "radial-gradient(ellipse 70% 60% at 50% 50%, black 0%, transparent 100%)",
        opacity: 0.5,
      }} />

      <div className="max-w-[1280px] mx-auto px-6 md:px-12 relative z-10">
        <div className="max-w-3xl mx-auto text-center">

          {/* Eyebrow — glass pill */}
          <div className="inline-flex items-center gap-2 mb-6 px-4 py-2 rounded-full"
            style={{
              background: "rgba(255,255,255,0.7)",
              backdropFilter: "blur(8px) saturate(180%)",
              WebkitBackdropFilter: "blur(8px) saturate(180%)",
              border: "1px solid rgba(255,255,255,0.9)",
              boxShadow: "0 2px 12px rgba(0,0,0,0.06), inset 0 1px 0 rgba(255,255,255,1)",
            }}>
            <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#0a0a0a", display: "inline-block", animation: "pulse-dot 2s ease-in-out infinite" }} />
            <span style={{ fontSize: "11px", fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase", color: "rgba(0,0,0,0.6)", fontFamily: "var(--font-mono,'Fira Code',monospace)" }}>
              Free &amp; Offline
            </span>
          </div>

          <h2 className="text-[42px] md:text-[56px] lg:text-[72px] font-semibold tracking-tight text-balance"
            style={{
              fontFamily: "var(--font-display,'Syne',sans-serif)",
              color: "#0a0a0a",
              letterSpacing: "-0.045em",
              lineHeight: 1.04,
            }}>
            Have a codebase?<br />
            <span style={{ color: "#0a0a0a", opacity: 0.45 }}>Let Cortex map it.</span>
          </h2>

          <p className="mt-6 text-base leading-[1.7] max-w-[480px] mx-auto" style={{ color: "rgba(0,0,0,0.45)" }}>
            Paste a GitHub URL and get architecture diagrams, learning paths, and interview prep in seconds. No signup. No API keys. No cloud.
          </p>

          {/* Pipeline badges — glass pills with connecting lines */}
          <div className="flex flex-wrap items-center justify-center gap-2 mt-10">
            {["Scan Repo", "Parse AST", "Build Graph", "Generate Artifacts"].map((step, i) => (
              <div key={step} className="flex items-center gap-2">
                <span style={{
                  padding: "6px 16px", borderRadius: "100px",
                  fontSize: "11px", fontWeight: 600,
                  background: "rgba(255,255,255,0.75)",
                  backdropFilter: "blur(8px) saturate(180%)",
                  WebkitBackdropFilter: "blur(8px) saturate(180%)",
                  border: "1px solid rgba(255,255,255,0.95)",
                  boxShadow: "0 2px 12px rgba(0,0,0,0.06), inset 0 1px 0 rgba(255,255,255,1)",
                  color: "#333",
                  letterSpacing: "0.04em",
                  fontFamily: "var(--font-mono,'Fira Code',monospace)",
                  transition: "all 0.25s ease",
                }}
                  onMouseEnter={e => {
                    (e.currentTarget as HTMLElement).style.background = "rgba(255,255,255,0.95)"
                    ;(e.currentTarget as HTMLElement).style.transform = "translateY(-2px)"
                  }}
                  onMouseLeave={e => {
                    (e.currentTarget as HTMLElement).style.background = "rgba(255,255,255,0.75)"
                    ;(e.currentTarget as HTMLElement).style.transform = "none"
                  }}>
                  {step}
                </span>
                {i < 3 && (
                  <span style={{ color: "rgba(0,0,0,0.18)", fontSize: "14px", fontWeight: 300 }}>→</span>
                )}
              </div>
            ))}
          </div>

          {/* CTAs */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mt-10">
            {/* Primary — Liquid Glass dark: layered depth, precise highlight */}
            <Link href="/dashboard"
              className="group inline-flex items-center justify-center gap-2 px-9 py-4 text-base font-semibold text-white rounded-full"
              style={{
                background: "#0a0a0a",
                // Three-layer shadow: diffuse lift + rim light + inner sheen
                boxShadow: [
                  "0 8px 32px rgba(0,0,0,0.22)",
                  "0 2px 6px rgba(0,0,0,0.14)",
                  "0 0 0 1px rgba(255,255,255,0.06)",
                  "inset 0 1px 0 rgba(255,255,255,0.10)",
                  "inset 0 -1px 0 rgba(0,0,0,0.24)",
                ].join(", "),
                transition: "transform 0.3s cubic-bezier(0.16,1,0.3,1), box-shadow 0.3s ease",
              }}
              onMouseEnter={e => {
                const el = e.currentTarget as HTMLElement
                el.style.transform = "translateY(-3px)"
                el.style.boxShadow = [
                  "0 16px 48px rgba(0,0,0,0.30)",
                  "0 4px 12px rgba(0,0,0,0.18)",
                  "0 0 0 1px rgba(255,255,255,0.08)",
                  "inset 0 1px 0 rgba(255,255,255,0.13)",
                  "inset 0 -1px 0 rgba(0,0,0,0.24)",
                ].join(", ")
              }}
              onMouseLeave={e => {
                const el = e.currentTarget as HTMLElement
                el.style.transform = ""
                el.style.boxShadow = [
                  "0 8px 32px rgba(0,0,0,0.22)",
                  "0 2px 6px rgba(0,0,0,0.14)",
                  "0 0 0 1px rgba(255,255,255,0.06)",
                  "inset 0 1px 0 rgba(255,255,255,0.10)",
                  "inset 0 -1px 0 rgba(0,0,0,0.24)",
                ].join(", ")
              }}>
              Analyze a Repository
              <ArrowUpRight className="w-4 h-4 transition-transform duration-300 group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
            </Link>

            {/* Secondary — Liquid Glass light: crisp dual-tone border */}
            <Link href="https://github.com/SUDHEER-KANDURU/cortex"
              target="_blank" rel="noopener noreferrer"
              className="inline-flex items-center justify-center gap-2 px-8 py-4 text-base font-medium rounded-full"
              style={{
                background: "rgba(255,255,255,0.68)",
                backdropFilter: "blur(12px) saturate(200%)",
                WebkitBackdropFilter: "blur(12px) saturate(200%)",
                // Dual-tone border: bright top, faint bottom
                border: "1px solid rgba(255,255,255,0.95)",
                borderBottom: "1px solid rgba(0,0,0,0.08)",
                boxShadow: [
                  "0 4px 20px rgba(0,0,0,0.07)",
                  "inset 0 1px 0 rgba(255,255,255,1)",
                  "inset 0 -1px 0 rgba(0,0,0,0.05)",
                ].join(", "),
                color: "rgba(0,0,0,0.68)",
                transition: "transform 0.3s cubic-bezier(0.16,1,0.3,1), box-shadow 0.3s ease, background 0.2s ease",
              }}
              onMouseEnter={e => {
                const el = e.currentTarget as HTMLElement
                el.style.transform = "translateY(-2px)"
                el.style.background = "rgba(255,255,255,0.88)"
                el.style.boxShadow = [
                  "0 8px 32px rgba(0,0,0,0.10)",
                  "inset 0 1px 0 rgba(255,255,255,1)",
                  "inset 0 -1px 0 rgba(0,0,0,0.05)",
                ].join(", ")
              }}
              onMouseLeave={e => {
                const el = e.currentTarget as HTMLElement
                el.style.transform = ""
                el.style.background = "rgba(255,255,255,0.68)"
                el.style.boxShadow = [
                  "0 4px 20px rgba(0,0,0,0.07)",
                  "inset 0 1px 0 rgba(255,255,255,1)",
                  "inset 0 -1px 0 rgba(0,0,0,0.05)",
                ].join(", ")
              }}>
              <Github className="w-4 h-4" />
              Star on GitHub
            </Link>
          </div>

          <p className="mt-8 text-xs" style={{ color: "rgba(0,0,0,0.25)", fontFamily: "var(--font-mono,'Fira Code',monospace)", letterSpacing: "0.06em" }}>
            MIT License · Built at SRMIST Chennai · Zero cloud dependencies
          </p>
        </div>
      </div>
    </section>
  )
}
