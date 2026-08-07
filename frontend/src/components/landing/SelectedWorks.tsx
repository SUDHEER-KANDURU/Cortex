"use client"

import type React from "react"
import Link from "next/link"
import { ArrowUpRight } from "lucide-react"
import { SectionTitle } from "@/components/ui/section-title"
import { DashboardLink } from "@/components/shared/DashboardLink"
import { useEffect, useRef, useState } from "react"
import { motion, useReducedMotion, useInView } from "framer-motion"
import { fadeUp, staggerContainer, staggerChild, SPRING, DURATION, EASE } from "@/lib/utils/motion"

// ── Visuals — ink palette only, zero blue/purple ──────────────────────────────

function ArchitectureDemoVisual({ onStart }: { onStart?: (startFn: () => void) => void }) {
  const [step, setStep] = useState(0)
  const [edgeStep, setEdgeStep] = useState(0)
  const [pulsing, setPulsing] = useState(0)

  useEffect(() => {
    if (!onStart) return
    onStart(() => {
      let s = 0
      // First animate nodes in
      const nodeTimer = setInterval(() => {
        if (document.visibilityState === 'hidden') return
        s += 1
        setStep(s)
        if (s >= 4) {
          clearInterval(nodeTimer)
          let e = 0
          const edgeTimer = setInterval(() => {
            if (document.visibilityState === 'hidden') return
            e += 1
            setEdgeStep(e)
            if (e >= 6) {
              clearInterval(edgeTimer)
              setPulsing(1)
            }
          }, 200)
        }
      }, 250)
    })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Pulse animation: cycle through edges
  useEffect(() => {
    if (!pulsing) return
    let p = 0
    const t = setInterval(() => {
      if (document.visibilityState === 'hidden') return
      p = (p + 1) % 6
      setPulsing(p + 1)
    }, 600)
    return () => clearInterval(t)
  }, [pulsing])

  // 2×2 grid layout
  const boxes = [
    { label: "api/",    x: 30,  y: 18,  fill: "#111" },
    { label: "domain/", x: 145, y: 18,  fill: "#444" },
    { label: "infra/",  x: 30,  y: 85,  fill: "#666" },
    { label: "shared/", x: 145, y: 85,  fill: "#888" },
  ]
  const cx = (i: number) => boxes[i].x + 40
  const cy = (i: number) => boxes[i].y + 13
  const edges = [
    { a: 0, b: 1, dash: false },
    { a: 0, b: 2, dash: false },
    { a: 1, b: 3, dash: false },
    { a: 2, b: 3, dash: true  },
    { a: 0, b: 3, dash: true  },
    { a: 1, b: 2, dash: true  },
  ]

  return (
    <div style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", padding: "16px", background: "var(--cx-visual-bg)", backdropFilter: "blur(8px) saturate(180%)", WebkitBackdropFilter: "blur(8px) saturate(180%)" }}>
      <svg viewBox="0 0 255 128" style={{ width: "100%", maxWidth: 255, overflow: "hidden" }}>
        {edges.map((e, i) => {
          const isActive = pulsing > 0 && ((pulsing - 1) % 6) === i
          return (
            <line key={i}
              x1={cx(e.a)} y1={cy(e.a)}
              x2={cx(e.b)} y2={cy(e.b)}
              stroke={edgeStep > i
                ? (isActive ? "var(--text)" : (e.dash ? "rgba(255,255,255,0.25)" : "rgba(255,255,255,0.45)"))
                : "rgba(255,255,255,0.06)"}
              strokeWidth={isActive ? 2 : (e.dash ? 1 : 1.5)}
              strokeDasharray={e.dash ? "4 3" : "none"}
              style={{ transition: "stroke 0.3s ease, stroke-width 0.3s ease" }} />
          )
        })}
        {boxes.map((box, i) => (
          <g key={i} style={{
            opacity: step > i ? 1 : 0,
            transform: step > i ? "none" : "translateY(8px)",
            transition: `opacity 0.35s ease ${i * 40}ms, transform 0.35s ease ${i * 40}ms`,
          }}>
            <rect x={box.x} y={box.y} width={80} height={26} rx={6}
              fill={step > i ? box.fill : "rgba(255,255,255,0.04)"}
              style={{ transition: "fill 0.35s ease" }} />
            <text x={box.x + 40} y={box.y + 17} textAnchor="middle"
              fontSize="9" fontWeight="600"
              fill={step > i ? "#fff" : "rgba(255,255,255,0.2)"}
              style={{ fontFamily: "var(--font-mono,'JetBrains Mono',monospace)", transition: "fill 0.35s ease" }}>
              {box.label}
            </text>
          </g>
        ))}
      </svg>
    </div>
  )
}

function LearningPathVisual() {
  const nodes = [
    { label: "Python Basics", x: 50,  done: true  },
    { label: "FastAPI",       x: 150, done: true  },
    { label: "SQLAlchemy",    x: 250, done: true  },
    { label: "Domain Models", x: 100, done: false },
    { label: "Use Cases",     x: 200, done: false },
    { label: "Graph Queries", x: 150, done: false },
  ]
  const yPos = [30, 70, 70, 110, 110, 145]
  const fills = ["rgba(255,255,255,0.85)","rgba(255,255,255,0.60)","rgba(255,255,255,0.40)","rgba(255,255,255,0.06)","rgba(255,255,255,0.06)","rgba(255,255,255,0.06)"]

  return (
    <div style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", padding: "20px", background: "var(--cx-visual-bg)", backdropFilter: "blur(8px) saturate(180%)", WebkitBackdropFilter: "blur(8px) saturate(180%)" }}>
      <svg viewBox="0 0 300 175" style={{ width: "100%", maxWidth: 300, overflow: "visible" }}>
        {[[0,1],[0,2],[1,3],[2,4],[3,5],[4,5]].map(([a, b], i) => (
          <line key={i}
            x1={nodes[a].x} y1={yPos[a] + 10}
            x2={nodes[b].x} y2={yPos[b]}
            stroke={nodes[a].done ? "rgba(255,255,255,0.35)" : "rgba(255,255,255,0.08)"}
            strokeWidth="1.5" strokeDasharray={nodes[a].done ? "none" : "4 3"} />
        ))}
        {nodes.map((n, i) => (
          <g key={i}>
            <rect x={n.x - 38} y={yPos[i]} width={76} height={20} rx={10} fill={fills[i]} />
            <text x={n.x} y={yPos[i] + 13} textAnchor="middle"
              fontSize="7" fontWeight="600"
              fill={n.done ? "#060810" : "rgba(255,255,255,0.3)"}
              style={{ fontFamily: "var(--font-mono,'JetBrains Mono',monospace)" }}>
              {n.label}
            </text>
          </g>
        ))}
      </svg>
    </div>
  )
}

function InterviewPrepVisual({ onStart }: { onStart?: (startFn: () => void) => void }) {
  const [idx, setIdx] = useState(0)
  const [revealed, setRevealed] = useState(false)
  const questions = [
    "What design pattern does JobRepository use?",
    "How does Celery handle task retries here?",
    "Explain the dependency between api/ and domain/",
  ]
  useEffect(() => {
    if (!onStart) return
    onStart(() => {
      setRevealed(true)
      // Cycle through questions with a delay
      let i = 0
      const t = setInterval(() => {
        if (document.visibilityState === 'hidden') return
        i = (i + 1) % questions.length
        setIdx(i)
      }, 1800)
      return () => clearInterval(t)
    })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  return (
    <div style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", padding: "20px", background: "var(--cx-visual-bg)", backdropFilter: "blur(8px) saturate(180%)", WebkitBackdropFilter: "blur(8px) saturate(180%)" }}>
      <div style={{ width: "100%", maxWidth: 300 }}>
        {questions.map((q, i) => (
          <div key={i} style={{
            padding: "8px 12px", marginBottom: "6px", borderRadius: "10px",
            fontSize: "10px", fontWeight: 500,
            fontFamily: "var(--font-mono,'JetBrains Mono',monospace)",
            border: `1px solid ${i === idx ? "var(--border-hover)" : "var(--border)"}`,
            background: i === idx ? "rgba(255,255,255,0.06)" : "rgba(255,255,255,0.02)",
            color: i === idx ? "var(--text)" : "var(--text-muted)",
            opacity: revealed ? 1 : 0,
            transition: "all 0.4s cubic-bezier(0.16,1,0.3,1)",
            transform: i === idx ? "translateX(4px)" : "none",
            display: "flex", alignItems: "center", gap: "8px",
          }}>
            <span style={{ fontSize: "8px", opacity: 0.45, color: "var(--text-muted)" }}>Q{i + 1}</span>
            {q}
          </div>
        ))}
        <div style={{
          marginTop: "8px", padding: "8px 12px", borderRadius: "10px",
          fontSize: "9px", fontFamily: "var(--font-mono,'JetBrains Mono',monospace)",
          background: "rgba(0,229,168,0.06)", border: "1px solid rgba(0,229,168,0.18)",
          color: "var(--primary)",
          opacity: revealed ? 1 : 0,
          transition: "opacity 0.5s ease 0.3s",
        }}>
          ✓ Model answer generated from your code
        </div>
      </div>
    </div>
  )
}

function VibeCodeVisual({ onStart }: { onStart?: (startFn: () => void) => void }) {
  const [revealed, setRevealed] = useState(false)
  const [highlight, setHighlight] = useState(-1)
  useEffect(() => {
    if (!onStart) return
    onStart(() => {
      setRevealed(true)
      // Pulse through each issue in sequence
      let i = 0
      const t = setInterval(() => {
        if (document.visibilityState === 'hidden') return
        setHighlight(i % 3)
        i++
      }, 1200)
      return () => clearInterval(t)
    })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const issues = [
    { line: "14", text: "Missing error handling", severity: "high", color: "#ef4444" },
    { line: "27", text: "Duplicate logic block",  severity: "med",  color: "#f59e0b" },
    { line: "41", text: "Inconsistent naming",    severity: "low",  color: "#555"    },
  ]

  return (
    <div style={{ width: "100%", height: "100%", display: "flex", alignItems: "center", justifyContent: "center", padding: "20px", background: "var(--cx-visual-bg)", backdropFilter: "blur(8px) saturate(180%)", WebkitBackdropFilter: "blur(8px) saturate(180%)" }}>
      <div style={{ width: "100%", maxWidth: 300, fontFamily: "var(--font-mono,'JetBrains Mono',monospace)" }}>
        <div style={{ marginBottom: "8px", fontSize: "9px", color: "var(--text-muted)", letterSpacing: "0.1em", textTransform: "uppercase",
          opacity: revealed ? 1 : 0, transition: "opacity 0.4s ease" }}>
          repository.py — 3 issues found
        </div>
        {issues.map((issue, i) => (
          <div key={i} style={{
            display: "flex", alignItems: "center", gap: "8px",
            padding: "7px 10px", marginBottom: "5px", borderRadius: "8px",
            border: `1px solid ${issue.color}40`,
            background: highlight === i ? `${issue.color}14` : `${issue.color}07`,
            opacity: revealed ? 1 : 0,
            transform: revealed ? "none" : "translateX(-8px)",
            transition: `opacity 0.4s ease ${i * 80}ms, transform 0.4s ease ${i * 80}ms, background 0.35s ease`,
            boxShadow: highlight === i ? `0 0 0 1px ${issue.color}40` : "none",
          }}>
            <span style={{ fontSize: "8px", color: issue.color, fontWeight: 700, minWidth: 24 }}>L{issue.line}</span>
            <span style={{ fontSize: "9px", color: "var(--text-secondary)", flex: 1 }}>{issue.text}</span>
            <span style={{ fontSize: "7px", fontWeight: 700, textTransform: "uppercase", color: issue.color, letterSpacing: "0.06em" }}>{issue.severity}</span>
          </div>
        ))}
        <div style={{ marginTop: "8px", display: "flex", alignItems: "center", gap: "6px", fontSize: "9px", color: "var(--text-muted)",
          opacity: revealed ? 1 : 0, transition: "opacity 0.5s ease 0.4s" }}>
          <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--success)", display: "inline-block" }} />
          LLM-free — static analysis only
        </div>
      </div>
    </div>
  )
}

interface Work {
  id: number; title: string; category: string; description: string
  Visual: React.FC<{ onStart?: (startFn: (() => (() => void) | void)) => void; active?: boolean }>
  tags: string[]; accent: string
}

function WorkCard({ work, index }: { work: Work; index: number }) {
  const cardRef = useRef<HTMLDivElement>(null)
  const hasPlayed = useRef(false)
  const startAnimationRef = useRef<(() => (() => void) | void) | null>(null)
  const cleanupRef = useRef<(() => void) | null>(null)
  const [inView, setInView] = useState(false)
  const prefersReduced = useReducedMotion()

  const handleRegisterStart = (startFn: (() => (() => void) | void)) => {
    startAnimationRef.current = startFn
  }

  useEffect(() => {
    const cardEl = cardRef.current
    if (!cardEl) return
    const obs = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting && !hasPlayed.current) {
        hasPlayed.current = true
        setInView(true)
        if (startAnimationRef.current) {
          const cleanup = startAnimationRef.current()
          if (typeof cleanup === 'function') cleanupRef.current = cleanup
        }
        obs.disconnect()
      }
    }, { threshold: 0.15 })
    obs.observe(cardEl)
    return () => {
      obs.disconnect()
      if (cleanupRef.current) { cleanupRef.current(); cleanupRef.current = null }
    }
  }, [])

  return (
    <div ref={cardRef} className="sticky" style={{ top: `${72 + index * 8}px`, zIndex: index + 1 }}>
      <motion.div
        className="pt-6"
        initial={prefersReduced ? false : { opacity: 0, y: 40 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, amount: 0.12 }}
        transition={{ duration: DURATION.reveal, delay: index * 0.06, ease: EASE.out }}
      >
        <DashboardLink className="group block">
          <motion.article
            data-spotlight
            className="cx-card overflow-hidden rounded-2xl md:rounded-3xl"
            style={{
              backdropFilter: "blur(24px) saturate(200%)",
              WebkitBackdropFilter: "blur(24px) saturate(200%)",
            }}
            whileHover={prefersReduced ? {} : {
              y: -6,
              boxShadow: "0 24px 64px rgba(0,0,0,0.22), 0 4px 16px rgba(0,0,0,0.12)",
              transition: SPRING.snappy,
            }}
          >
            <div className="cx-visual-bg relative overflow-hidden"
              style={{ height: "200px", borderBottom: "1px solid var(--cx-card-border)", backdropFilter: "blur(8px)" }}>
              <work.Visual onStart={handleRegisterStart} active={inView} />
              <div className="cx-pill" style={{
                position: "absolute", top: "12px", left: "12px",
                padding: "3px 10px", borderRadius: "100px",
                fontSize: "9px", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase",
                backdropFilter: "blur(12px) saturate(180%)",
                WebkitBackdropFilter: "blur(12px) saturate(180%)",
                fontFamily: "var(--font-mono,'JetBrains Mono',monospace)",
              }}>
                {work.category}
              </div>
            </div>

            <div className="p-5 md:p-6">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h3 className="cx-text text-lg md:text-xl font-semibold">{work.title}</h3>
                  <p className="cx-text-muted text-sm mt-1.5 leading-relaxed">{work.description}</p>
                </div>
                {/* Arrow — rotates & shifts on group hover via CSS */}
                <motion.div
                  className="cx-arrow-circle flex-shrink-0 mt-0.5 w-8 h-8 rounded-full flex items-center justify-center"
                  whileHover={prefersReduced ? {} : { scale: 1.15, backgroundColor: "#000", transition: SPRING.snappy }}
                >
                  <ArrowUpRight className="cx-arrow-color w-4 h-4 transition-all duration-300 group-hover:!text-white group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
                </motion.div>
              </div>
              <div className="flex flex-wrap gap-2 mt-4">
                {work.tags.map(tag => (
                  <span key={tag} className="cx-tag px-3 py-1 text-xs font-medium rounded-full">
                    {tag}
                  </span>
                ))}
              </div>
            </div>
          </motion.article>
        </DashboardLink>
      </motion.div>
    </div>
  )
}

const works: Work[] = [
  { id: 1, title: "Architecture Diagram Generator", category: "Code Intelligence",
    description: "Auto-generates Mermaid flowcharts showing every module, dependency, and service boundary in your codebase.",
    Visual: ArchitectureDemoVisual, tags: ["AST Parsing", "Neo4j", "Mermaid"], accent: "#111" },
  { id: 2, title: "Learning Path Builder", category: "Developer Education",
    description: "Identifies every concept and pattern in your repository and creates a personalised curriculum ordered from fundamentals to advanced.",
    Visual: LearningPathVisual, tags: ["Knowledge Graph", "NLP", "FastAPI"], accent: "#444" },
  { id: 3, title: "Interview Prep Engine", category: "Career Tools",
    description: "Generates technical questions grounded in your actual project code with model answers. Walk into any interview prepared.",
    Visual: InterviewPrepVisual, tags: ["Graph Queries", "Python", "Celery"], accent: "#d97706" },
  { id: 4, title: "Vibe Code Detector", category: "Code Quality",
    description: "Flags AI-generated anti-patterns — missing error handling, duplicate logic, inconsistent naming — and explains exactly how to fix each one.",
    Visual: VibeCodeVisual, tags: ["Static Analysis", "LLM-free", "Neo4j"], accent: "#ef4444" },
]

export function PortfolioSelectedWorks() {
  return (
    <section id="works" className="py-20 md:py-10 md:pt-32 pb-4"
      style={{
        borderTop: "1px solid var(--cx-card-border)",
        background: "var(--cx-section-bg)",
        backdropFilter: "saturate(200%) blur(24px)",
        WebkitBackdropFilter: "saturate(200%) blur(24px)",
      }}>
      <div className="max-w-[1280px] mx-auto px-6 md:px-12">
        <div className="flex items-center justify-between mb-12 md:mb-16">
          <div>
            <p className="cx-eyebrow" style={{
              fontSize: "10px", fontWeight: 700, letterSpacing: "0.16em",
              textTransform: "uppercase",
              fontFamily: "var(--font-mono,'JetBrains Mono',monospace)", marginBottom: "8px",
            }}>
              Outputs
            </p>
            <SectionTitle className="text-3xl md:text-4xl lg:text-[52px] font-semibold tracking-tight">
              Capabilities
            </SectionTitle>
          </div>
          <DashboardLink
            className="cx-link hidden md:inline-flex items-center gap-2 text-sm font-medium transition-all duration-200 hover:gap-3">
            Launch App
            <ArrowUpRight className="w-4 h-4" />
          </DashboardLink>
        </div>
        <div className="relative">
          {works.map((work, index) => <WorkCard key={work.id} work={work} index={index} />)}
        </div>
        <div className="md:hidden mt-8 text-center">
          <DashboardLink
            className="cx-link cx-row inline-flex items-center gap-2 px-6 py-3 text-sm font-medium rounded-full transition-colors">
            Launch App <ArrowUpRight className="w-4 h-4" />
          </DashboardLink>
        </div>
      </div>
    </section>
  )
}


