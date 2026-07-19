"use client"

import Link from "next/link"
import { ArrowDown, GitBranch, Cpu, Database, FileCode } from "lucide-react"
import { useEffect, useRef, useState } from "react"
import dynamic from "next/dynamic"

// Lazy-load the heavy 3D RepoTree only after the page has painted.
// A CSS skeleton placeholder is shown until then — no layout shift.
const RepoTree = dynamic(() => import("@/features/tree/RepoTree"), {
  ssr: false,
  loading: () => (
    <div style={{
      width: "100%", height: "100%",
      display: "flex", flexDirection: "column",
      justifyContent: "flex-end", padding: "24px",
    }}>
      {/* Skeleton lines — mimic a tree structure */}
      {[80, 60, 70, 45, 55, 38, 65].map((w, i) => (
        <div key={i} style={{
          height: "10px", borderRadius: "5px", marginBottom: "10px",
          marginLeft: `${i % 3 === 0 ? 0 : i % 3 === 1 ? 16 : 32}px`,
          width: `${w}%`,
          background: "rgba(255,255,255,0.07)",
          animation: "pulse-skeleton 1.6s ease-in-out infinite",
          animationDelay: `${i * 120}ms`,
        }} />
      ))}
    </div>
  ),
})

// Delay-mount the heavy component until idle to not block first paint
function LazyRepoTree({ progress }: { progress: React.MutableRefObject<number> }) {
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    if (typeof window === "undefined") return
    let idleId: number | undefined
    let timeoutId: ReturnType<typeof setTimeout> | undefined

    if (typeof requestIdleCallback !== "undefined") {
      idleId = requestIdleCallback(() => setMounted(true), { timeout: 2000 })
    } else {
      timeoutId = setTimeout(() => setMounted(true), 400)
    }

    return () => {
      if (idleId !== undefined) cancelIdleCallback(idleId)
      if (timeoutId !== undefined) clearTimeout(timeoutId)
    }
  }, [])

  if (!mounted) {
    return (
      <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column", justifyContent: "flex-end", padding: "24px" }}>
        {[80, 60, 70, 45, 55, 38, 65].map((w, i) => (
          <div key={i} style={{
            height: "10px", borderRadius: "5px", marginBottom: "10px",
            marginLeft: `${i % 3 === 0 ? 0 : i % 3 === 1 ? 16 : 32}px`,
            width: `${w}%`,
            background: "rgba(255,255,255,0.07)",
            animation: "pulse-skeleton 1.6s ease-in-out infinite",
            animationDelay: `${i * 120}ms`,
          }} />
        ))}
      </div>
    )
  }

  return <RepoTree progress={progress} />
}

const PIPELINE_STEPS = [
  { icon: GitBranch, label: "Scan Repo" },
  { icon: Cpu,       label: "Parse AST" },
  { icon: Database,  label: "Build Graph" },
  { icon: FileCode,  label: "Generate" },
]

export function PortfolioHero() {
  const titleText = "Understand any codebase with AI reasoning"
  const words = titleText.split(" ")

  const progressRef = useRef(0)
  const spacerRef   = useRef<HTMLDivElement>(null)
  const [isDesktop, setIsDesktop] = useState(false)
  const [activeStep, setActiveStep] = useState(0)

  useEffect(() => {
    const check = () => setIsDesktop(window.innerWidth >= 768)
    check()
    window.addEventListener("resize", check)

    const handleScroll = () => {
      const spacer = spacerRef.current
      if (!spacer) return
      const top    = spacer.getBoundingClientRect().top + window.scrollY
      const height = spacer.offsetHeight - window.innerHeight
      const raw    = (window.scrollY - top) / height
      progressRef.current = Math.max(0, Math.min(1, raw))
    }

    handleScroll()
    window.addEventListener("scroll", handleScroll, { passive: true })
    const interval = setInterval(() => setActiveStep(s => (s + 1) % PIPELINE_STEPS.length), 1800)

    return () => {
      window.removeEventListener("resize", check)
      window.removeEventListener("scroll", handleScroll)
      clearInterval(interval)
    }
  }, [])

  return (
    <>
      <div ref={spacerRef} style={{ height: "500vh", position: "relative" }}>
        <div style={{
          position: "sticky", top: 0, height: "100vh",
          overflow: "hidden", paddingTop: "80px",
          background: "rgba(255,255,255,0.72)",
          backdropFilter: "blur(10px) saturate(180%)",
          WebkitBackdropFilter: "blur(10px) saturate(180%)",
        }}>
          <div className="max-w-[1280px] mx-auto px-6 md:px-12 h-full grid grid-cols-1 md:grid-cols-2 gap-8 items-center">

            {/* ── Left: hero copy ── */}
            <div>
              {/* Eyebrow badge — liquid glass */}
              <div className="hero-eyebrow inline-flex items-center gap-2 mb-6 px-3 py-1.5 rounded-full"
                style={{
                  background: "rgba(255,255,255,0.65)",
                  backdropFilter: "blur(8px) saturate(200%)",
                  WebkitBackdropFilter: "blur(8px) saturate(200%)",
                  border: "1px solid rgba(255,255,255,0.88)",
                  boxShadow: "0 2px 12px rgba(0,0,0,0.06), inset 0 1px 0 rgba(255,255,255,1)",
                }}>
                <span style={{
                  width: 6, height: 6, borderRadius: "50%",
                  background: "#111", display: "inline-block",
                  animation: "pulse-dot 2s ease-in-out infinite",
                }} />
                <span style={{
                  fontSize: "11px", fontWeight: 600, letterSpacing: "0.1em",
                  textTransform: "uppercase", color: "rgba(0,0,0,0.65)",
                  fontFamily: "var(--font-mono,'Fira Code',monospace)",
                }}>
                  Engineering Reasoning Engine
                </span>
              </div>

              <h1 className="text-[42px] sm:text-[54px] lg:text-[68px] font-semibold tracking-tight leading-[1.04] text-balance"
                style={{ fontFamily: "var(--font-display,'Syne',system-ui,sans-serif)", letterSpacing: "-0.045em" }}>
                {words.map((word, index) => (
                  <span
                    key={index}
                    className="hero-word py-1 font-semibold"
                    style={{
                      display: "inline-block",
                      animationDelay: `${index * 0.08}s`,
                      marginRight: index < words.length - 1 ? "0.22em" : "0",
                    }}
                  >
                    {word}
                  </span>
                ))}
              </h1>

              <p className="mt-5 max-w-[400px] leading-[1.65] text-[15px]" style={{ color: "rgba(0,0,0,0.42)" }}>
                Paste any GitHub URL. Cortex parses your repository at the AST level, constructs a Neo4j knowledge graph, and generates architecture diagrams, learning paths, and interview prep — fully offline, zero API keys.
              </p>

              {/* CTAs */}
              <div className="flex flex-row flex-wrap items-center gap-3 mt-8">
                {/* Primary — Liquid Glass dark: same treatment as FinalCTA */}
                <Link href="/dashboard"
                  data-magnetic
                  className="hero-cta-primary cta-shimmer inline-flex items-center justify-center px-7 py-3.5 text-sm font-semibold text-white rounded-full"
                  style={{
                    background: "#111",
                    boxShadow: [
                      "0 4px 20px rgba(0,0,0,0.20)",
                      "0 1px 4px rgba(0,0,0,0.14)",
                      "0 0 0 1px rgba(255,255,255,0.06)",
                      "inset 0 1px 0 rgba(255,255,255,0.10)",
                      "inset 0 -1px 0 rgba(0,0,0,0.22)",
                    ].join(", "),
                    transition: "transform 0.3s cubic-bezier(0.16,1,0.3,1), box-shadow 0.3s ease",
                  }}
                  onMouseEnter={e => {
                    e.currentTarget.style.transform = "translateY(-2px)"
                    e.currentTarget.style.boxShadow = [
                      "0 8px 28px rgba(0,0,0,0.28)",
                      "0 2px 6px rgba(0,0,0,0.16)",
                      "0 0 0 1px rgba(255,255,255,0.08)",
                      "inset 0 1px 0 rgba(255,255,255,0.12)",
                      "inset 0 -1px 0 rgba(0,0,0,0.22)",
                    ].join(", ")
                  }}
                  onMouseLeave={e => {
                    e.currentTarget.style.transform = ""
                    e.currentTarget.style.boxShadow = [
                      "0 4px 20px rgba(0,0,0,0.20)",
                      "0 1px 4px rgba(0,0,0,0.14)",
                      "0 0 0 1px rgba(255,255,255,0.06)",
                      "inset 0 1px 0 rgba(255,255,255,0.10)",
                      "inset 0 -1px 0 rgba(0,0,0,0.22)",
                    ].join(", ")
                  }}>
                  Analyze a Repository
                </Link>

                {/* Secondary — Liquid Glass light: dual-tone border */}
                <Link href="#works"
                  data-magnetic
                  className="inline-flex items-center gap-2 px-5 py-3 text-sm font-medium rounded-full"
                  style={{
                    color: "rgba(0,0,0,0.58)",
                    background: "rgba(255,255,255,0.62)",
                    backdropFilter: "blur(12px) saturate(180%)",
                    WebkitBackdropFilter: "blur(12px) saturate(180%)",
                    border: "1px solid rgba(255,255,255,0.90)",
                    borderBottom: "1px solid rgba(0,0,0,0.06)",
                    boxShadow: [
                      "0 2px 10px rgba(0,0,0,0.05)",
                      "inset 0 1px 0 rgba(255,255,255,1)",
                      "inset 0 -1px 0 rgba(0,0,0,0.04)",
                    ].join(", "),
                    transition: "background 0.2s ease, box-shadow 0.2s ease, gap 0.25s ease",
                  }}
                  onMouseEnter={e => {
                    e.currentTarget.style.background = "rgba(255,255,255,0.80)"
                    e.currentTarget.style.boxShadow = [
                      "0 4px 16px rgba(0,0,0,0.08)",
                      "inset 0 1px 0 rgba(255,255,255,1)",
                      "inset 0 -1px 0 rgba(0,0,0,0.04)",
                    ].join(", ")
                  }}
                  onMouseLeave={e => {
                    e.currentTarget.style.background = "rgba(255,255,255,0.62)"
                    e.currentTarget.style.boxShadow = [
                      "0 2px 10px rgba(0,0,0,0.05)",
                      "inset 0 1px 0 rgba(255,255,255,1)",
                      "inset 0 -1px 0 rgba(0,0,0,0.04)",
                    ].join(", ")
                  }}>
                  See Capabilities
                  <ArrowDown className="w-3.5 h-3.5" />
                </Link>
              </div>

              {/* Pipeline mini-preview — monochrome */}
              <div className="mt-10 flex items-center gap-0" aria-label="How Cortex works">
                {PIPELINE_STEPS.map((step, i) => {
                  const Icon = step.icon
                  const isActive = i === activeStep
                  return (
                    <div key={step.label} className="flex items-center">
                      <div className="hero-pipeline-step flex flex-col items-center gap-1.5"
                        style={{ transition: "all 0.4s cubic-bezier(0.16,1,0.3,1)" }}>
                        <div className="flex items-center justify-center w-9 h-9 rounded-full"
                          style={{
                            background: isActive
                              ? "rgba(10,10,10,0.88)"
                              : "rgba(255,255,255,0.65)",
                            backdropFilter: isActive ? "none" : "blur(12px) saturate(180%)",
                            WebkitBackdropFilter: isActive ? "none" : "blur(12px) saturate(180%)",
                            border: isActive
                              ? "1px solid rgba(0,0,0,0.2)"
                              : "1px solid rgba(255,255,255,0.9)",
                            boxShadow: isActive
                              ? "0 4px 16px rgba(0,0,0,0.2)"
                              : "0 2px 8px rgba(0,0,0,0.06), inset 0 1px 0 rgba(255,255,255,1)",
                            transform: isActive ? "scale(1.12)" : "scale(1)",
                            transition: "all 0.35s cubic-bezier(0.16,1,0.3,1)",
                          }}>
                          <Icon className="w-3.5 h-3.5"
                            style={{ color: isActive ? "#fff" : "rgba(0,0,0,0.35)", transition: "color 0.3s" }} />
                        </div>
                        <span style={{
                          fontSize: "9px", fontWeight: 600, letterSpacing: "0.08em",
                          textTransform: "uppercase", whiteSpace: "nowrap",
                          color: isActive ? "#111" : "rgba(0,0,0,0.28)",
                          transition: "color 0.3s",
                          fontFamily: "var(--font-mono,'Fira Code',monospace)",
                        }}>{step.label}</span>
                      </div>
                      {i < PIPELINE_STEPS.length - 1 && (
                        <div style={{
                          width: "28px", height: "1.5px",
                          margin: "0 2px", marginBottom: "14px",
                          background: i < activeStep
                            ? "linear-gradient(90deg, rgba(10,10,10,0.6), rgba(10,10,10,0.3))"
                            : "rgba(0,0,0,0.1)",
                          borderRadius: "1px",
                          transition: "background 0.5s ease",
                        }} />
                      )}
                    </div>
                  )
                })}
              </div>

              <p className="mt-6 text-xs tracking-widest uppercase" style={{ color: "rgba(0,0,0,0.2)" }}>
                Scroll to grow the repository tree ↓
              </p>
            </div>

            {/* ── Right: 3D repository tree (dark panel) ── */}
            <div style={{
              height: "100%", position: "relative",
              opacity: isDesktop ? 1 : 0,
              pointerEvents: isDesktop ? "auto" : "none",
              transition: "opacity 0.6s ease",
            }}>
              <div style={{
                position: "absolute", inset: "16px 0",
                borderRadius: "24px",
                background: "#0a0a0a",
                boxShadow: "0 0 0 1px rgba(255,255,255,0.07), 0 12px 60px rgba(0,0,0,0.45)",
                overflow: "hidden",
              }}>
                {/* Window chrome */}
                <div style={{
                  position: "absolute", top: "14px", left: "16px",
                  zIndex: 10, display: "flex", gap: "6px", pointerEvents: "none",
                }}>
                  <span style={{ width: 10, height: 10, borderRadius: "50%", background: "#FF5F57", display: "block" }} />
                  <span style={{ width: 10, height: 10, borderRadius: "50%", background: "#FFBD2E", display: "block" }} />
                  <span style={{ width: 10, height: 10, borderRadius: "50%", background: "#28C840", display: "block" }} />
                </div>

                {/* Label — liquid glass dark pill */}
                <div style={{
                  position: "absolute", top: "12px", left: "50%",
                  transform: "translateX(-50%)",
                  zIndex: 10, pointerEvents: "none",
                  display: "flex", alignItems: "center", gap: "8px",
                  background: "rgba(255,255,255,0.08)",
                  backdropFilter: "blur(8px) saturate(180%)",
                  WebkitBackdropFilter: "blur(8px) saturate(180%)",
                  border: "1px solid rgba(255,255,255,0.14)",
                  boxShadow: "0 2px 12px rgba(0,0,0,0.2), inset 0 1px 0 rgba(255,255,255,0.1)",
                  borderRadius: "100px", padding: "5px 14px", whiteSpace: "nowrap",
                }}>
                  <span style={{
                    width: "6px", height: "6px", borderRadius: "50%",
                    background: "#aaa", display: "inline-block",
                    animation: "pulse-dot 2s ease-in-out infinite",
                  }} />
                  <span style={{
                    fontSize: "10px", fontWeight: 600, letterSpacing: "0.14em",
                    textTransform: "uppercase", color: "rgba(255,255,255,0.5)",
                    fontFamily: "var(--font-mono,'Fira Code',monospace)",
                  }}>
                    Live Repository Graph
                  </span>
                </div>

                <LazyRepoTree progress={progressRef} />

                {/* Bottom fade */}
                <div style={{
                  position: "absolute", bottom: 0, left: 0, right: 0,
                  height: "80px",
                  background: "linear-gradient(to top,#0a0a0a 0%,transparent 100%)",
                  pointerEvents: "none", zIndex: 5,
                }} />              </div>
            </div>

          </div>
        </div>
      </div>
    </>
  )
}
