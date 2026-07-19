"use client"

import { SectionTitle } from "@/components/ui/section-title"
import { useEffect, useRef, useState } from "react"
import gsap from "gsap"

function useInView(threshold = 0.3) {
  const ref = useRef<HTMLDivElement>(null)
  const [inView, setInView] = useState(false)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const obs = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting) setInView(true) },
      { threshold },
    )
    obs.observe(el)
    return () => obs.disconnect()
  }, [threshold])
  return { ref, inView }
}

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

function ParsingAnimation({ active }: { active: boolean }) {
  const [activeLine, setActiveLine] = useState(0)
  const lines = [
    { text: "class JobRepository:",           color: "#555" },
    { text: "  def create(self, job):",        color: "#333" },
    { text: "    # → Neo4j node created",      color: "#28c840" },
    { text: "  def find_by_id(id):",           color: "#333" },
    { text: "    # → Graph edge traversed",    color: "#28c840" },
    { text: "  async def list_all():",         color: "#333" },
    { text: "    # → Cypher query generated",  color: "#28c840" },
  ]
  useEffect(() => {
    if (!active) return
    const t = setInterval(() => setActiveLine(l => (l + 1) % lines.length), 900)
    return () => clearInterval(t)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active])

  return (
    <div style={{ background: "#0a0a0a", borderRadius: "16px", overflow: "hidden", border: "1px solid rgba(255,255,255,0.08)", boxShadow: "0 8px 40px rgba(0,0,0,0.2)" }}>
      <div style={{ background: "#111", borderBottom: "1px solid rgba(255,255,255,0.06)", padding: "10px 16px", display: "flex", alignItems: "center", gap: "8px" }}>
        <span style={{ width: 10, height: 10, borderRadius: "50%", background: "#FF5F57", display: "block" }} />
        <span style={{ width: 10, height: 10, borderRadius: "50%", background: "#FFBD2E", display: "block" }} />
        <span style={{ width: 10, height: 10, borderRadius: "50%", background: "#28C840", display: "block" }} />
        <span style={{ marginLeft: "auto", fontSize: "10px", fontFamily: "var(--font-mono,'Fira Code',monospace)", color: "rgba(255,255,255,0.3)", letterSpacing: "0.08em" }}>
          repository.py
        </span>
      </div>
      <div style={{ padding: "16px 20px" }}>
        {lines.map((line, i) => (
          <div key={i} style={{
            fontFamily: "var(--font-mono,'Fira Code',monospace)", fontSize: "12px", lineHeight: "1.9",
            color: i === activeLine ? line.color : "rgba(255,255,255,0.25)",
            background: i === activeLine ? "rgba(255,255,255,0.04)" : "transparent",
            borderRadius: "4px", padding: "1px 6px",
            transition: "all 0.3s ease",
            borderLeft: i === activeLine ? `2px solid ${line.color}` : "2px solid transparent",
          }}>
            {line.text}
            {i === activeLine && (
              <span style={{ display: "inline-block", width: "7px", height: "13px", background: line.color, marginLeft: "2px", verticalAlign: "middle", animation: "caret-blink 0.9s step-end infinite" }} />
            )}
          </div>
        ))}
      </div>
      <div style={{ borderTop: "1px solid rgba(255,255,255,0.05)", padding: "8px 16px", display: "flex", alignItems: "center", gap: "12px", background: "#0d0d0d" }}>
        <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#28C840", display: "inline-block", boxShadow: "0 0 6px #28C840" }} />
        <span style={{ fontSize: "10px", color: "rgba(255,255,255,0.35)", fontFamily: "var(--font-mono,'Fira Code',monospace)", letterSpacing: "0.06em" }}>
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
  { value: 241, suffix: "+", label: "Graph Nodes",      sub: "per avg repo"       },
  { value: 0,   suffix: "",  label: "API Keys Required", sub: "runs fully offline" },
  { value: 6,   suffix: "",  label: "Artifact Types",    sub: "generated per scan" },
]

export function PortfolioAbout() {
  const { ref: statsRef, inView: statsVisible } = useInView(0.3)
  const { ref: codeRef,  inView: codeVisible  } = useInView(0.2)

  return (
    <section id="about" className="py-20 md:py-10 md:pb-32 md:pt-32"
      style={{
        borderTop: "1px solid rgba(255,255,255,0.9)",
        background: "rgba(255,255,255,0.72)",
        backdropFilter: "saturate(180%) blur(20px)",
        WebkitBackdropFilter: "saturate(180%) blur(20px)",
      }}>
      <div className="max-w-[1280px] mx-auto px-6 md:px-12">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-20 mb-16 md:mb-24">
          <div data-reveal="up">
            <p style={{
              fontSize: "10px", fontWeight: 700, letterSpacing: "0.16em",
              textTransform: "uppercase", color: "rgba(0,0,0,0.35)",
              fontFamily: "var(--font-mono,'Fira Code',monospace)", marginBottom: "10px",
            }}>
              About
            </p>
            <SectionTitle className="text-3xl md:text-4xl lg:text-[52px] font-semibold tracking-tight text-balance">
              Bridging Static Code &amp; Structural Understanding
            </SectionTitle>
            <p className="mt-6 text-muted-foreground leading-relaxed">
              Cortex reads your repository at the AST level, constructs a rich knowledge graph in Neo4j, and generates artifacts that explain the system — not just describe it.
            </p>
            <p className="mt-4 text-muted-foreground leading-relaxed">
              Built at SRMIST Chennai. Runs entirely on your machine. No API keys, no cloud billing, no data leaving your environment.
            </p>
            <div ref={statsRef} className="grid grid-cols-3 gap-3 mt-10" data-stagger>
              {stats.map(stat => (
                <div key={stat.label}
                  className="text-center p-4 rounded-2xl transition-all duration-300 hover:-translate-y-1"
                  style={{
                    background: "rgba(255,255,255,0.65)",
                    backdropFilter: "blur(8px) saturate(180%)",
                    WebkitBackdropFilter: "blur(8px) saturate(180%)",
                    border: "1px solid rgba(255,255,255,0.88)",
                    boxShadow: "0 4px 20px rgba(0,0,0,0.06), inset 0 1px 0 rgba(255,255,255,1)",
                  }}>
                  <div className="text-2xl md:text-3xl font-semibold" style={{ color: "#111" }}>
                    <AnimatedNumber value={stat.value} suffix={stat.suffix} active={statsVisible} />
                  </div>
                  <div className="text-xs font-semibold mt-1">{stat.label}</div>
                  <div className="text-xs text-muted-foreground mt-0.5">{stat.sub}</div>
                </div>
              ))}
            </div>
          </div>
          <div ref={codeRef} data-reveal="up" data-spotlight style={{ transitionDelay: "150ms" }}>
            <ParsingAnimation active={codeVisible} />
          </div>
        </div>

        <div data-reveal="up">
          <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground mb-5">
            Built on production-grade open-source
          </h3>
          <div className="flex flex-wrap gap-2" data-stagger>
            {skills.map(skill => (
              <span key={skill}
                className="px-4 py-2 text-sm font-medium rounded-full"
                style={{
                  background: "rgba(255,255,255,0.65)",
                  backdropFilter: "blur(12px) saturate(160%)",
                  WebkitBackdropFilter: "blur(12px) saturate(160%)",
                  border: "1px solid rgba(255,255,255,0.88)",
                  boxShadow: "0 2px 8px rgba(0,0,0,0.04), inset 0 1px 0 rgba(255,255,255,1)",
                  color: "rgba(0,0,0,0.6)",
                  cursor: "default",
                }}
                onMouseEnter={e => gsap.to(e.currentTarget, { y: -2, boxShadow: '0 4px 12px rgba(0,0,0,0.08)', duration: 0.2, ease: 'power2.out' })}
                onMouseLeave={e => gsap.to(e.currentTarget, { y: 0, boxShadow: 'none', duration: 0.2, ease: 'power2.out' })}
              >
                {skill}
              </span>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}
