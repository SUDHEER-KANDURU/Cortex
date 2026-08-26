"use client"

import { SectionTitle } from "@/components/ui/section-title"
import { useEffect, useRef, useState } from "react"
import { motion, useReducedMotion, useInView } from "framer-motion"
import { fadeUp, staggerContainer, staggerChild, SPRING, DURATION, EASE } from "@/lib/utils/motion"

// ── useInViewOnce — fires once when element enters viewport ─────────────────
function useInViewOnce(threshold = 0.3) {
  const ref = useRef<HTMLDivElement>(null)
  const [inView, setInView] = useState(false)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const obs = new IntersectionObserver(
      ([e]) => { if (e.isIntersecting) { setInView(true); obs.disconnect() } },
      { threshold }
    )
    obs.observe(el)
    return () => obs.disconnect()
  }, [threshold])
  return { ref, inView }
}

// ── AnimatedNumber — counts from 0 to value using rAF ────────────────────────
function AnimatedNumber({ value, suffix = "", active }: { value: number; suffix?: string; active: boolean }) {
  const [display, setDisplay] = useState(0)
  const started = useRef(false)
  const rafId = useRef<number | null>(null)

  useEffect(() => {
    if (!active || started.current) return
    started.current = true
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      setDisplay(value)
      return
    }
    const start = performance.now()
    const tick = (now: number) => {
      const p = Math.min((now - start) / 1200, 1)
      setDisplay(Math.round((1 - Math.pow(1 - p, 3)) * value))
      if (p < 1) {
        rafId.current = requestAnimationFrame(tick)
      } else {
        rafId.current = null
      }
    }
    rafId.current = requestAnimationFrame(tick)
    return () => {
      if (rafId.current !== null) {
        cancelAnimationFrame(rafId.current)
        rafId.current = null
      }
    }
  }, [active, value])

  return <span>{display}{suffix}</span>
}

// ── Parsing code animation ────────────────────────────────────────────────────
function ParsingAnimation({ active }: { active: boolean }) {
  const [activeLine, setActiveLine] = useState(0)
  const lines = [
    { text: "class JobRepository:",          color: "#e4e4e7" },
    { text: "  def create(self, job):",       color: "#a1a1aa" },
    { text: "    # → Neo4j node created",     color: "#34d399" },
    { text: "  def find_by_id(id):",          color: "#a1a1aa" },
    { text: "    # → Graph edge traversed",   color: "#34d399" },
    { text: "  async def list_all():",        color: "#a1a1aa" },
    { text: "    # → Cypher query generated", color: "#34d399" },
  ]
  useEffect(() => {
    if (!active) return
    const t = setInterval(() => {
      if (document.visibilityState === 'hidden') return
      setActiveLine(l => (l + 1) % lines.length)
    }, 900)
    return () => clearInterval(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active])

  return (
    <div style={{
      background: "rgba(18, 20, 24, 0.88)", borderRadius: "16px", overflow: "hidden",
      border: "1px solid rgba(255,255,255,0.10)",
      boxShadow: "0 16px 48px rgba(0,0,0,0.28), 0 4px 12px rgba(0,0,0,0.18)",
    }}>
      {/* Chrome bar */}
      <div style={{
        background: "rgba(30, 32, 36, 0.92)", borderBottom: "1px solid rgba(255,255,255,0.08)",
        padding: "10px 16px", display: "flex", alignItems: "center", gap: "8px",
      }}>
        <span style={{ width: 10, height: 10, borderRadius: "50%", background: "#E07070", display: "block" }} />
        <span style={{ width: 10, height: 10, borderRadius: "50%", background: "#D4A055", display: "block" }} />
        <span style={{ width: 10, height: 10, borderRadius: "50%", background: "#6AAF7C", display: "block" }} />
        <span style={{ marginLeft: "auto", fontSize: "10px", fontFamily: "var(--font-mono)", color: "rgba(160,160,170,0.7)", letterSpacing: "0.08em" }}>
          repository.py
        </span>
      </div>
      {/* Code body */}
      <div style={{ padding: "16px 20px" }}>
        {lines.map((line, i) => (
          <motion.div
            key={i}
            animate={{
              color: i === activeLine ? line.color : "#52525b",
              backgroundColor: i === activeLine ? "rgba(255,255,255,0.06)" : "transparent",
              x: i === activeLine ? 2 : 0,
            }}
            transition={{ duration: 0.25, ease: EASE.out }}
            style={{
              fontFamily: "var(--font-mono)", fontSize: "12px", lineHeight: "1.9",
              borderRadius: "4px", padding: "1px 6px",
              borderLeft: `2px solid ${i === activeLine ? line.color : "transparent"}`,
            }}>
            {line.text}
            {i === activeLine && (
              <span style={{
                display: "inline-block", width: "7px", height: "13px",
                background: line.color, marginLeft: "2px", verticalAlign: "middle",
                animation: "caret-blink 0.9s step-end infinite",
              }} />
            )}
          </motion.div>
        ))}
      </div>
      {/* Status bar */}
      <div style={{
        borderTop: "1px solid rgba(255,255,255,0.08)", padding: "8px 16px",
        display: "flex", alignItems: "center", gap: "12px",
        background: "rgba(30, 32, 36, 0.92)",
      }}>
        <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#34d399", display: "inline-block" }} />
        <span style={{ fontSize: "10px", color: "rgba(160,160,170,0.75)", fontFamily: "var(--font-mono)", letterSpacing: "0.06em" }}>
          AST parsing active · 241 nodes mapped
        </span>
      </div>
    </div>
  )
}

const skills = [
  "AST Parsing", "Neo4j Graph DB", "FastAPI", "Python 3.12",
  "Celery Workers", "PostgreSQL", "Redis", "React Flow",
  "Next.js 14", "Architecture Analysis", "Knowledge Graphs", "LLM-Free",
]
const stats = [
  { value: 241, suffix: "+", label: "Graph Nodes",       sub: "per avg repo"       },
  { value: 0,   suffix: "",  label: "API Keys Required",  sub: "runs fully offline" },
  { value: 6,   suffix: "",  label: "Artifact Types",     sub: "generated per scan" },
]

export function PortfolioAbout() {
  const prefersReduced = useReducedMotion()
  const { ref: statsRef, inView: statsVisible } = useInViewOnce(0.3)
  const { ref: codeRef,  inView: codeVisible  } = useInViewOnce(0.2)

  // Section in-view for orchestrating stagger
  const sectionRef = useRef<HTMLElement>(null)
  const isInView = useInView(sectionRef, { once: true, amount: 0.1 })

  return (
    <section
      id="about"
      ref={sectionRef}
      className="py-16 md:py-20"
      style={{
        borderTop: "1px solid var(--cx-card-border)",
        background: "var(--cx-section-bg)",
        backdropFilter: "saturate(200%) blur(24px)",
        WebkitBackdropFilter: "saturate(200%) blur(24px)",
      }}>
      <div className="max-w-[1280px] mx-auto px-6 md:px-12">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-10 lg:gap-14 mb-10 md:mb-14">

          {/* ── Left column ── */}
          <motion.div
            variants={prefersReduced ? undefined : fadeUp}
            initial={prefersReduced ? false : "hidden"}
            animate={isInView ? "visible" : "hidden"}
            data-reveal="up"
          >
            <p className="cx-eyebrow" style={{
              fontSize: "10px", fontWeight: 700, letterSpacing: "0.16em",
              textTransform: "uppercase",
              fontFamily: "var(--font-mono,'JetBrains Mono',monospace)", marginBottom: "10px",
            }}>
              About
            </p>
            <SectionTitle className="text-3xl md:text-4xl lg:text-[52px] font-semibold tracking-tight text-balance">
              Bridging Static Code &amp; Structural Understanding
            </SectionTitle>
            <p className="cx-text-muted mt-6 leading-relaxed">
              Cortex reads your repository at the AST level, constructs a rich knowledge graph in Neo4j,
              and generates artifacts that explain the system — not just describe it.
            </p>
            <p className="cx-text-muted mt-4 leading-relaxed">
              Built at SRMIST Chennai. Runs entirely on your machine. No API keys, no cloud billing,
              no data leaving your environment.
            </p>

            {/* Stats — staggered counter entrance */}
            <motion.div
              ref={statsRef}
              variants={prefersReduced ? undefined : staggerContainer}
              initial={prefersReduced ? false : "hidden"}
              animate={statsVisible ? "visible" : "hidden"}
              className="grid grid-cols-3 gap-3 mt-6"
              data-stagger
            >
              {stats.map(stat => (
                <motion.div
                  key={stat.label}
                  variants={prefersReduced ? undefined : staggerChild}
                  whileHover={prefersReduced ? {} : { y: -4, transition: SPRING.snappy }}
                  className="cx-stat-card text-center p-4 rounded-2xl"
                  style={{
                    backdropFilter: "blur(8px) saturate(180%)",
                    WebkitBackdropFilter: "blur(8px) saturate(180%)",
                  }}>
                  <div className="cx-stat-number text-2xl md:text-3xl font-semibold">
                    <AnimatedNumber value={stat.value} suffix={stat.suffix} active={statsVisible} />
                  </div>
                  <div className="cx-text text-xs font-semibold mt-1">{stat.label}</div>
                  <div className="cx-text-muted text-xs mt-0.5">{stat.sub}</div>
                </motion.div>
              ))}
            </motion.div>
          </motion.div>

          {/* ── Right: code animation panel ── */}
          <motion.div
            ref={codeRef}
            variants={prefersReduced ? undefined : {
              hidden: { opacity: 0, x: 32, filter: "blur(6px)" },
              visible: {
                opacity: 1, x: 0, filter: "blur(0px)",
                transition: { duration: DURATION.reveal, delay: 0.15, ease: EASE.out },
              },
            }}
            initial={prefersReduced ? false : "hidden"}
            animate={isInView ? "visible" : "hidden"}
            data-reveal="up"
            data-spotlight
            style={{ transitionDelay: "150ms" }}
          >
            <ParsingAnimation active={codeVisible} />
          </motion.div>
        </div>

        {/* ── Skills row ── */}
        <motion.div
          variants={prefersReduced ? undefined : fadeUp}
          initial={prefersReduced ? false : "hidden"}
          animate={isInView ? "visible" : "hidden"}
          transition={{ delay: 0.3 }}
          data-reveal="up"
        >
          <h3 className="cx-text-muted text-sm font-semibold uppercase tracking-wider mb-5">
            Built on production-grade open-source
          </h3>
          <motion.div
            variants={prefersReduced ? undefined : staggerContainer}
            initial={prefersReduced ? false : "hidden"}
            animate={isInView ? "visible" : "hidden"}
            className="flex flex-wrap gap-2"
            data-stagger
          >
            {skills.map(skill => (
              <motion.span
                key={skill}
                variants={prefersReduced ? undefined : staggerChild}
                whileHover={prefersReduced ? {} : { y: -3, scale: 1.04, transition: SPRING.snappy }}
                whileTap={prefersReduced ? {} : { scale: 0.97 }}
                className="cx-tag px-4 py-2 text-sm font-medium rounded-full"
                style={{
                  backdropFilter: "blur(12px) saturate(160%)",
                  WebkitBackdropFilter: "blur(12px) saturate(160%)",
                  cursor: "default",
                }}
              >
                {skill}
              </motion.span>
            ))}
          </motion.div>
        </motion.div>
      </div>
    </section>
  )
}
