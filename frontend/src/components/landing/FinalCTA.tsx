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

          <h2 className="text-4xl md:text-5xl lg:text-[64px] font-semibold tracking-tight text-balance leading-[1.05]"
            style={{ fontFamily: "var(--font-display,'Syne',sans-serif)", color: "#0a0a0a" }}>
            Have a codebase?<br />
            <span style={{ color: "#0a0a0a", opacity: 0.55 }}>Let Cortex map it.</span>
          </h2>

          <p className="mt-6 text-lg leading-relaxed max-w-xl mx-auto" style={{ color: "rgba(0,0,0,0.5)" }}>
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
            {/* Primary — solid black */}
            <Link href="/dashboard"
              className="group inline-flex items-center justify-center gap-2 px-9 py-4 text-base font-semibold text-white rounded-full transition-all duration-300 hover:-translate-y-1.5"
              style={{
                background: "#0a0a0a",
                boxShadow: "0 8px 32px rgba(0,0,0,0.22), 0 2px 6px rgba(0,0,0,0.12)",
              }}
              onMouseEnter={e => {
                const el = e.currentTarget as HTMLElement
                el.style.boxShadow = "0 16px 48px rgba(0,0,0,0.32), 0 4px 12px rgba(0,0,0,0.16)"
              }}
              onMouseLeave={e => {
                const el = e.currentTarget as HTMLElement
                el.style.boxShadow = "0 8px 32px rgba(0,0,0,0.22), 0 2px 6px rgba(0,0,0,0.12)"
              }}>
              Analyze a Repository
              <ArrowUpRight className="w-4 h-4 transition-transform duration-300 group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
            </Link>

            {/* Secondary — glass */}
            <Link href="https://github.com/SUDHEER-KANDURU/cortex"
              target="_blank" rel="noopener noreferrer"
              className="inline-flex items-center justify-center gap-2 px-8 py-4 text-base font-medium rounded-full transition-all duration-300 hover:-translate-y-1"
              style={{
                background: "rgba(255,255,255,0.72)",
                backdropFilter: "blur(8px) saturate(180%)",
                WebkitBackdropFilter: "blur(8px) saturate(180%)",
                border: "1px solid rgba(255,255,255,0.95)",
                boxShadow: "0 4px 20px rgba(0,0,0,0.07), inset 0 1px 0 rgba(255,255,255,1)",
                color: "rgba(0,0,0,0.7)",
              }}
              onMouseEnter={e => {
                const el = e.currentTarget as HTMLElement
                el.style.background = "rgba(255,255,255,0.92)"
                el.style.boxShadow = "0 8px 32px rgba(0,0,0,0.1), inset 0 1px 0 rgba(255,255,255,1)"
              }}
              onMouseLeave={e => {
                const el = e.currentTarget as HTMLElement
                el.style.background = "rgba(255,255,255,0.72)"
                el.style.boxShadow = "0 4px 20px rgba(0,0,0,0.07), inset 0 1px 0 rgba(255,255,255,1)"
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
