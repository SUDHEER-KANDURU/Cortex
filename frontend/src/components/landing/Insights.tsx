"use client"

import Link from "next/link"
import { ArrowUpRight } from "lucide-react"
import { SectionTitle } from "@/components/ui/section-title"
import { motion, useReducedMotion } from "framer-motion"
import { SectionReveal } from "@/components/shared/PageTransition"
import { staggerFastContainer, staggerFastChild, SPRING } from "@/lib/utils/motion"

// ── Card visuals — pure CSS, no SVG ──────────────────────────────────────────

function AstVisual() {
  return (
    <div style={{
      width: "100%", height: "100%",
      display: "flex", flexDirection: "column",
      justifyContent: "center", gap: 8, padding: "0 4px",
      fontFamily: "var(--font-mono, 'JetBrains Mono', monospace)",
    }}>
      {/* Tree row 1 — root */}
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <span style={{ fontSize: 10, color: "var(--primary)", fontWeight: 700, opacity: 0.9 }}>
          Module
        </span>
        <div style={{ flex: 1, height: 1, background: "rgba(255,255,255,0.07)" }} />
        <span style={{ fontSize: 9, color: "var(--text-muted)", opacity: 0.6 }}>root</span>
      </div>
      {/* Tree row 2 */}
      <div style={{ display: "flex", alignItems: "center", gap: 8, paddingLeft: 16 }}>
        <span style={{ fontSize: 9, color: "var(--text-muted)", marginRight: -4 }}>└─</span>
        <span style={{ fontSize: 10, color: "var(--primary)", fontWeight: 600 }}>ClassDef</span>
        <span style={{ fontSize: 9, color: "var(--text-muted)", opacity: 0.5, marginLeft: 4 }}>PaymentService</span>
      </div>
      {/* Tree row 3 */}
      <div style={{ display: "flex", alignItems: "center", gap: 8, paddingLeft: 32 }}>
        <span style={{ fontSize: 9, color: "var(--text-muted)", opacity: 0.6, marginRight: -4 }}>└─</span>
        <span style={{ fontSize: 10, color: "var(--primary)", opacity: 0.7, fontWeight: 600 }}>FunctionDef</span>
        <span style={{ fontSize: 9, color: "var(--text-muted)", opacity: 0.5, marginLeft: 4 }}>process()</span>
      </div>
      {/* Tree row 4 */}
      <div style={{ display: "flex", alignItems: "center", gap: 8, paddingLeft: 48 }}>
        <span style={{ fontSize: 9, color: "var(--text-muted)", opacity: 0.4, marginRight: -4 }}>└─</span>
        <span style={{ fontSize: 10, color: "var(--primary)", opacity: 0.5 }}>Call</span>
        <span style={{ fontSize: 9, color: "var(--text-muted)", opacity: 0.4, marginLeft: 4 }}>validate_card()</span>
      </div>
      {/* Bottom label */}
      <div style={{ display: "flex", gap: 12, marginTop: 2 }}>
        <span style={{ fontSize: 9, color: "var(--text-muted)", opacity: 0.5 }}>depth: 4</span>
        <span style={{ fontSize: 9, color: "var(--text-muted)", opacity: 0.5 }}>nodes: 312</span>
        <span style={{ fontSize: 9, color: "var(--text-muted)", opacity: 0.5 }}>parse: 38ms</span>
      </div>
    </div>
  )
}

function GraphVisual() {
  const stats: Array<{ label: string; value: string; accent?: string }> = [
    { label: "Nodes",  value: "241", accent: "var(--primary)" },
    { label: "Edges",  value: "387", accent: "var(--primary)" },
    { label: "Files",         value: "34"  },
    { label: "Classes",       value: "18"  },
    { label: "Functions",     value: "156" },
    { label: "Graph build",   value: "3.9s" },
  ]
  return (
    <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column", justifyContent: "center", gap: 7 }}>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "5px 10px" }}>
        {stats.map(s => (
          <div key={s.label} style={{ display: "flex", flexDirection: "column", gap: 1 }}>
            <span style={{
              fontSize: 15, fontWeight: 800, lineHeight: 1,
              fontFamily: "var(--font-mono, 'JetBrains Mono', monospace)",
              color: s.accent ?? "var(--text)",
            }}>
              {s.value}
            </span>
            <span style={{ fontSize: 9, color: "var(--text-muted)", opacity: 0.6, letterSpacing: "0.04em" }}>
              {s.label}
            </span>
          </div>
        ))}
      </div>
      <div style={{
        marginTop: 4, height: 3, borderRadius: 2,
        background: "rgba(255,255,255,0.06)", overflow: "hidden",
      }}>
        <div style={{ width: "72%", height: "100%", background: "var(--primary)", borderRadius: 2, opacity: 0.7 }} />
      </div>
      <span style={{ fontSize: 9, color: "var(--text-muted)", opacity: 0.5, fontFamily: "var(--font-mono)", letterSpacing: "0.04em" }}>
        relationship coverage · typical Python repo
      </span>
    </div>
  )
}

function OfflineVisual() {
  const checks = [
    { label: "AST parser",       done: true  },
    { label: "Graph builder",    done: true  },
    { label: "Metrics engine",   done: true  },
    { label: "OpenAI API",       done: false },
    { label: "External services",done: false },
  ]
  return (
    <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column", justifyContent: "center", gap: 6 }}>
      {checks.map(c => (
        <div key={c.label} style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{
            width: 14, height: 14, borderRadius: "50%", flexShrink: 0,
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 8, fontWeight: 800,
            background: c.done ? "var(--primary-dim)" : "var(--danger-dim)",
            color: c.done ? "var(--primary)" : "var(--danger)",
            border: `1px solid ${c.done ? "var(--border-hover)" : "var(--danger-dim)"}`,
          }}>
            {c.done ? "✓" : "✕"}
          </span>
          <span style={{
            fontSize: 11,
            color: c.done ? "var(--text-secondary)" : "var(--text-muted)",
            opacity: c.done ? 0.85 : 0.4,
            fontFamily: "var(--font-mono, 'JetBrains Mono', monospace)",
            textDecoration: c.done ? "none" : "line-through",
          }}>
            {c.label}
          </span>
        </div>
      ))}
    </div>
  )
}

// ── Card data ─────────────────────────────────────────────────────────────────

const insights = [
  {
    id: 1,
    title: "Why AST Parsing Beats Text Search for Code Understanding",
    excerpt: "Cortex walks your codebase at the syntax-tree level — tracking call graphs, class hierarchies, and nesting depth — not with grep. Here's why that matters for structural analysis.",
    date: "Dec 2025", readTime: "5 min read", tag: "Deep Dive",
    visual: <AstVisual />,
  },
  {
    id: 2,
    title: "Building a Knowledge Graph from Source Code",
    excerpt: "How Cortex maps 241 nodes and 387 relationships from a typical Python repository into a queryable graph in under 4 seconds — and what you can do with it.",
    date: "Nov 2025", readTime: "7 min read", tag: "Architecture",
    visual: <GraphVisual />,
  },
  {
    id: 3,
    title: "Offline-First Engineering Tools — The Case for Zero API Keys",
    excerpt: "Why developer tooling should run on your machine, not in the cloud — and how Cortex delivers production-quality analysis without a single external API call.",
    date: "Nov 2025", readTime: "4 min read", tag: "Philosophy",
    visual: <OfflineVisual />,
  },
]

// ── Section ───────────────────────────────────────────────────────────────────

export function PortfolioInsights() {
  const prefersReduced = useReducedMotion()

  return (
    <section
      id="insights"
      className="py-20 md:py-32"
      style={{
        borderTop: "1px solid var(--cx-card-border)",
        background: "var(--cx-section-bg)",
        backdropFilter: "blur(20px) saturate(200%)",
        WebkitBackdropFilter: "blur(20px) saturate(200%)",
      }}
    >
      <div className="max-w-[1280px] mx-auto px-6 md:px-12">

        {/* Header */}
        <div className="flex items-center justify-between mb-12 md:mb-16">
          <SectionReveal>
            <p
              className="cx-eyebrow"
              style={{
                fontSize: "10px", fontWeight: 700, letterSpacing: "0.16em",
                textTransform: "uppercase", marginBottom: "10px",
                fontFamily: "var(--font-mono, 'JetBrains Mono', monospace)",
              }}
            >
              Writing
            </p>
            <SectionTitle className="text-3xl md:text-4xl lg:text-[52px] font-semibold tracking-tight">
              Insights
            </SectionTitle>
          </SectionReveal>
          <Link
            href="https://github.com/SUDHEER-KANDURU/cortex"
            target="_blank"
            rel="noopener noreferrer"
            className="cx-link hidden md:inline-flex items-center gap-2 text-sm font-medium transition-all duration-200 hover:gap-3"
          >
            View on GitHub <ArrowUpRight className="w-4 h-4" />
          </Link>
        </div>

        {/* Cards */}
        <motion.div
          className="grid grid-cols-1 md:grid-cols-3 gap-5 md:gap-6"
          variants={prefersReduced ? undefined : staggerFastContainer}
          initial={prefersReduced ? false : "hidden"}
          whileInView="visible"
          viewport={{ once: true, amount: 0.1 }}
        >
          {insights.map((item) => (
            <motion.div key={item.id} variants={prefersReduced ? undefined : staggerFastChild}>
              <Link
                href="https://github.com/SUDHEER-KANDURU/cortex"
                target="_blank"
                rel="noopener noreferrer"
                className="group block h-full"
              >
                <motion.article
                  className="cx-card h-full rounded-2xl overflow-hidden"
                  data-spotlight
                  style={{
                    backdropFilter: "blur(8px) saturate(180%)",
                    WebkitBackdropFilter: "blur(8px) saturate(180%)",
                  }}
                  whileHover={prefersReduced ? {} : {
                    y: -6,
                    boxShadow: "var(--shadow-lg), var(--edge-top)",
                    transition: SPRING.snappy,
                  }}
                >
                  {/* Visual area — no SVG */}
                  <div
                    className="cx-visual-bg"
                    style={{
                      height: "120px", overflow: "hidden",
                      borderBottom: "1px solid var(--cx-card-border)",
                      padding: "14px 18px",
                      display: "flex", alignItems: "stretch",
                    }}
                  >
                    {item.visual}
                  </div>

                  {/* Content */}
                  <div className="p-5">
                    <div className="flex items-center justify-between mb-3">
                      <span
                        className="cx-pill"
                        style={{
                          fontSize: "9px", fontWeight: 700, letterSpacing: "0.1em",
                          textTransform: "uppercase", padding: "3px 10px", borderRadius: "100px",
                          backdropFilter: "blur(12px)", WebkitBackdropFilter: "blur(12px)",
                          fontFamily: "var(--font-mono, 'JetBrains Mono', monospace)",
                        }}
                      >
                        {item.tag}
                      </span>
                      <div className="cx-text-muted flex items-center gap-2 text-xs">
                        <span>{item.date}</span>
                        <span>·</span>
                        <span>{item.readTime}</span>
                      </div>
                    </div>
                    <h3 className="cx-text text-base font-semibold leading-snug transition-opacity duration-200 group-hover:opacity-60">
                      {item.title}
                    </h3>
                    <p className="cx-text-muted text-sm mt-2 leading-relaxed">
                      {item.excerpt}
                    </p>
                    <div className="cx-link flex items-center gap-1.5 mt-4 text-xs font-semibold transition-all duration-200 group-hover:gap-2.5">
                      Read more <ArrowUpRight className="w-3 h-3" />
                    </div>
                  </div>
                </motion.article>
              </Link>
            </motion.div>
          ))}
        </motion.div>

        {/* Mobile CTA */}
        <div className="md:hidden mt-8 text-center">
          <Link
            href="https://github.com/SUDHEER-KANDURU/cortex"
            target="_blank"
            rel="noopener noreferrer"
            className="cx-link cx-row inline-flex items-center gap-2 px-6 py-3 text-sm font-medium rounded-full transition-colors"
          >
            View on GitHub <ArrowUpRight className="w-4 h-4" />
          </Link>
        </div>
      </div>
    </section>
  )
}
