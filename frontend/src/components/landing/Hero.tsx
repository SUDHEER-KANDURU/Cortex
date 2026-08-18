"use client"

import Link from "next/link"
import { ArrowDown, GitBranch, Cpu, Database, FileCode } from "lucide-react"
import { useEffect, useRef, useState } from "react"
import { motion, useReducedMotion } from "framer-motion"
import { DashboardLink } from "@/components/shared/DashboardLink"
import dynamic from "next/dynamic"
import { fadeUp, heroWord, staggerContainer, DURATION, EASE, SPRING } from "@/lib/utils/motion"

// Lazy-load the heavy 3D RepoTree only after the page has painted.
const RepoTree = dynamic(() => import("@/features/tree/RepoTree"), {
  ssr: false,
  loading: () => (
    <div style={{
      width: "100%", height: "100%",
      display: "flex", flexDirection: "column",
      justifyContent: "flex-end", padding: "24px",
    }}>
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
  const prefersReducedMotion = useReducedMotion()

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

    const interval = setInterval(() => {
      if (document.visibilityState === 'hidden') return
      setActiveStep(s => (s + 1) % PIPELINE_STEPS.length)
    }, 1800)

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
          background: "transparent",
        }}>
          <div className="max-w-[1280px] mx-auto px-6 md:px-12 h-full grid grid-cols-1 md:grid-cols-2 gap-8 items-center">

            {/* ── Left: hero copy ── */}
            <motion.div
              variants={prefersReducedMotion ? undefined : staggerContainer}
              initial={prefersReducedMotion ? false : "hidden"}
              animate="visible"
            >
              {/* Eyebrow badge */}
              <motion.div
                variants={prefersReducedMotion ? undefined : fadeUp}
                className="hero-eyebrow inline-flex items-center gap-2 mb-6 px-3 py-1.5 rounded-full"
                style={{
                  background: "var(--cx-pill-bg)",
                  backdropFilter: "blur(8px) saturate(200%)",
                  WebkitBackdropFilter: "blur(8px) saturate(200%)",
                  border: "1px solid var(--cx-pill-border)",
                  boxShadow: "0 2px 12px rgba(0,0,0,0.15), inset 0 1px 0 rgba(255,255,255,0.08)",
                }}>
                <span style={{
                  width: 6, height: 6, borderRadius: "50%",
                  background: "var(--primary)", display: "inline-block",
                  animation: "pulse-dot 2s ease-in-out infinite",
                  boxShadow: "0 0 6px var(--primary)",
                }} />
                <span style={{
                  fontSize: "11px", fontWeight: 600, letterSpacing: "0.1em",
                  textTransform: "uppercase", color: "var(--cx-pill-text)",
                  fontFamily: "var(--font-mono,'JetBrains Mono',monospace)",
                }}>
                  Engineering Reasoning Engine
                </span>
              </motion.div>

              {/* Hero headline — word-by-word reveal */}
              <h1 className="text-[42px] sm:text-[54px] lg:text-[68px] font-semibold tracking-tight leading-[1.04] text-balance"
                style={{ fontFamily: "var(--font-sans,'Inter',system-ui,sans-serif)", letterSpacing: "-0.045em", color: "var(--text)" }}>
                {words.map((word, index) => (
                  prefersReducedMotion ? (
                    <span key={index} style={{ display: "inline-block", marginRight: index < words.length - 1 ? "0.22em" : "0" }}>
                      {word}
                    </span>
                  ) : (
                    <motion.span
                      key={index}
                      custom={index}
                      variants={heroWord}
                      initial="hidden"
                      animate="visible"
                      style={{
                        display: "inline-block",
                        marginRight: index < words.length - 1 ? "0.22em" : "0",
                        color: "var(--text)",
                      }}
                    >
                      {word}
                    </motion.span>
                  )
                ))}
              </h1>

              {/* Subtitle */}
              <motion.p
                variants={prefersReducedMotion ? undefined : {
                  hidden: { opacity: 0, y: 16 },
                  visible: { opacity: 1, y: 0, transition: { duration: DURATION.reveal, delay: words.length * 0.085 + 0.1, ease: EASE.out } },
                }}
                className="mt-5 max-w-[400px] leading-[1.65] text-[15px]"
                style={{ color: "var(--text-secondary)" }}>
                Paste any GitHub URL. Cortex parses your repository at the AST level, constructs a Neo4j knowledge graph, and generates architecture diagrams, learning paths, and interview prep — fully offline, zero API keys.
              </motion.p>

              {/* CTAs */}
              <motion.div
                variants={prefersReducedMotion ? undefined : {
                  hidden: { opacity: 0, y: 18 },
                  visible: { opacity: 1, y: 0, transition: { duration: DURATION.reveal, delay: words.length * 0.085 + 0.22, ease: EASE.out } },
                }}
                className="flex flex-row flex-wrap items-center gap-3 mt-8"
              >
                {/* Primary CTA — spring lift on hover */}
                <motion.div
                  whileHover={prefersReducedMotion ? {} : { y: -3, transition: SPRING.snappy }}
                  whileTap={prefersReducedMotion ? {} : { scale: 0.96, transition: { duration: DURATION.micro } }}
                >
                  <DashboardLink
                    className="hero-cta-primary cta-shimmer inline-flex items-center justify-center px-7 py-3.5 text-sm font-semibold rounded-full"
                    style={{
                      background: "linear-gradient(135deg, var(--primary) 0%, #00c9a7 100%)",
                      color: "#060810",
                      boxShadow: "0 4px 20px var(--primary-glow), inset 0 1px 0 rgba(255,255,255,0.22)",
                    }}>
                    Analyze a Repository
                  </DashboardLink>
                </motion.div>

                {/* Secondary CTA */}
                <motion.div
                  whileHover={prefersReducedMotion ? {} : { y: -2, transition: SPRING.snappy }}
                  whileTap={prefersReducedMotion ? {} : { scale: 0.97, transition: { duration: DURATION.micro } }}
                >
                  <Link href="#works"
                    className="inline-flex items-center gap-2 px-5 py-3 text-sm font-medium rounded-full"
                    style={{
                      color: "var(--text-secondary)",
                      background: "var(--cx-pill-bg)",
                      backdropFilter: "blur(12px) saturate(180%)",
                      WebkitBackdropFilter: "blur(12px) saturate(180%)",
                      border: "1px solid var(--cx-pill-border)",
                      boxShadow: "0 2px 10px rgba(0,0,0,0.1)",
                      transition: "background 0.2s ease, box-shadow 0.2s ease, color 0.2s ease",
                    }}
                    onMouseEnter={e => {
                      e.currentTarget.style.background = "var(--cx-arrow-bg)"
                      e.currentTarget.style.color = "var(--text)"
                    }}
                    onMouseLeave={e => {
                      e.currentTarget.style.background = "var(--cx-pill-bg)"
                      e.currentTarget.style.color = "var(--text-secondary)"
                    }}>
                    See Capabilities
                    <motion.span
                      animate={prefersReducedMotion ? {} : { y: [0, 3, 0] }}
                      transition={{ duration: 1.8, repeat: Infinity, ease: "easeInOut" }}
                    >
                      <ArrowDown className="w-3.5 h-3.5" />
                    </motion.span>
                  </Link>
                </motion.div>
              </motion.div>

              {/* Pipeline mini-preview */}
              <motion.div
                variants={prefersReducedMotion ? undefined : {
                  hidden: { opacity: 0, y: 20 },
                  visible: { opacity: 1, y: 0, transition: { duration: DURATION.reveal, delay: words.length * 0.085 + 0.35, ease: EASE.out } },
                }}
                className="mt-10 flex items-center gap-0"
                aria-label="How Cortex works"
              >
                {PIPELINE_STEPS.map((step, i) => {
                  const Icon = step.icon
                  const isActive = i === activeStep
                  return (
                    <div key={step.label} className="flex items-center">
                      <div className="hero-pipeline-step flex flex-col items-center gap-1.5">
                        <motion.div
                          animate={prefersReducedMotion ? {} : {
                            scale: isActive ? 1.12 : 1,
                            boxShadow: isActive
                              ? "0 0 14px var(--primary-glow)"
                              : "none",
                          }}
                          transition={SPRING.snappy}
                          className="flex items-center justify-center w-9 h-9 rounded-full"
                          style={{
                            background: isActive ? "var(--primary-dim)" : "var(--cx-pill-bg)",
                            backdropFilter: "blur(8px) saturate(160%)",
                            WebkitBackdropFilter: "blur(8px) saturate(160%)",
                            border: isActive
                              ? "1px solid rgba(0,229,168,0.35)"
                              : "1px solid var(--cx-pill-border)",
                          }}>
                          <motion.div
                            animate={prefersReducedMotion ? {} : { rotate: isActive ? [0, 8, -8, 0] : 0 }}
                            transition={{ duration: 0.5, ease: EASE.out }}
                          >
                            <Icon className="w-3.5 h-3.5"
                              style={{ color: isActive ? "var(--primary)" : "var(--text-muted)", transition: "color 0.3s" }} />
                          </motion.div>
                        </motion.div>
                        <span style={{
                          fontSize: "9px", fontWeight: 600, letterSpacing: "0.08em",
                          textTransform: "uppercase", whiteSpace: "nowrap",
                          color: isActive ? "var(--text)" : "var(--text-muted)",
                          transition: "color 0.3s",
                          fontFamily: "var(--font-mono,'JetBrains Mono',monospace)",
                        }}>{step.label}</span>
                      </div>

                      {i < PIPELINE_STEPS.length - 1 && (
                        <div aria-hidden="true" style={{
                          width: "28px", height: "1.5px",
                          margin: "0 2px", marginBottom: "14px",
                          background: i < activeStep
                            ? "linear-gradient(90deg, var(--primary), rgba(0,229,168,0.3))"
                            : "var(--border)",
                          borderRadius: "1px",
                          transition: "background 0.5s ease",
                        }} />
                      )}
                    </div>
                  )
                })}
              </motion.div>

              <motion.p
                variants={prefersReducedMotion ? undefined : {
                  hidden: { opacity: 0 },
                  visible: { opacity: 1, transition: { duration: DURATION.medium, delay: words.length * 0.085 + 0.55 } },
                }}
                className="mt-6 text-xs tracking-widest uppercase"
                style={{ color: "var(--text-muted)", fontFamily: "var(--font-mono)" }}>
                Scroll to grow the repository tree ↓
              </motion.p>
            </motion.div>

            {/* ── Right: 3D repo tree — slides in from right ── */}
            <motion.div
              initial={prefersReducedMotion ? false : { opacity: 0, x: 40 }}
              animate={{ opacity: isDesktop ? 1 : 0, x: 0 }}
              transition={{ duration: DURATION.major, delay: 0.3, ease: EASE.out }}
              data-hero-panel
              style={{
                height: "100%", position: "relative",
                pointerEvents: isDesktop ? "auto" : "none",
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

                {/* Label */}
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
                    fontFamily: "var(--font-mono,'JetBrains Mono',monospace)",
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
                }} />
              </div>
            </motion.div>

          </div>
        </div>
      </div>
    </>
  )
}
