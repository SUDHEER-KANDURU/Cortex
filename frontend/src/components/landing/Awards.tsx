"use client"

import { ArrowUpRight } from "lucide-react"
import Link from "next/link"
import { SectionTitle } from "@/components/ui/section-title"
import { motion, useReducedMotion } from "framer-motion"
import { SectionReveal } from "@/components/shared/PageTransition"
import { SPRING, staggerFastContainer, staggerFastChild } from "@/lib/utils/motion"

const awards = [
  { title: "AST-Level Parsing",       year: "Core",      metric: "100%",  metricLabel: "structural",   organization: "Full abstract syntax tree analysis — not just text grep. Every symbol, import, and call extracted.",                     link: "#about" },
  { title: "Neo4j Knowledge Graph",   year: "Core",      metric: "241+",  metricLabel: "nodes / repo", organization: "241 nodes and 387 relationships mapped per average repository into a queryable graph.",                                link: "#about" },
  { title: "AI-Powered Chat & Reasoning", year: "Feature", metric: "NIM",  metricLabel: "AI engine",    organization: "Conversational AI interface powered by NVIDIA NIM with intelligent rule-based fallback.",                              link: "/dashboard" },
  { title: "6 Artifact Types",        year: "Output",    metric: "6",     metricLabel: "per scan",     organization: "Architecture diagrams, learning paths, API specs, interview prep, vibe code reports & onboarding guides.",             link: "/dashboard" },
  { title: "Full-Text Search & Navigation", year: "Feature", metric: "FTS5", metricLabel: "instant",  organization: "Search across all artifacts and code structures. Navigate from architecture to individual functions.",                   link: "/dashboard" },
  { title: "Blast Radius Analysis",   year: "Feature",   metric: "graph", metricLabel: "traversal",   organization: "Visualize the impact of changes across dependent modules — know what breaks before you ship.",                          link: "/dashboard" },
  { title: "Celery Async Pipeline",   year: "Infra",     metric: "async", metricLabel: "non-blocking", organization: "Background workers handle large repos without blocking the UI. Real-time job status polling.",                          link: "#about" },
  { title: "Incremental Analysis",    year: "Core",      metric: "Δ only", metricLabel: "re-scan",     organization: "Only re-analyzes changed files on subsequent scans — faster iterations on large repositories.",                          link: "/dashboard" },
  { title: "Docker-First Deployment", year: "DevOps",    metric: "1 cmd", metricLabel: "full stack",   organization: "Single docker-compose up spins database, workers, API, and frontend. Zero config friction.",                           link: "https://github.com/SUDHEER-KANDURU/cortex" },
]

export function PortfolioAwards() {
  const prefersReduced = useReducedMotion()

  return (
    <section id="awards" className="py-16 md:py-20"
      style={{ borderTop: "1px solid var(--cx-card-border)", background: "var(--cx-section-bg)" }}>
      <div className="max-w-[1280px] mx-auto px-6 md:px-12">

        <SectionReveal className="mb-10 md:mb-12">
          <p className="cx-eyebrow" style={{ fontSize: "10px", fontWeight: 700, letterSpacing: "0.16em", textTransform: "uppercase", fontFamily: "var(--font-mono,'JetBrains Mono',monospace)", marginBottom: "10px" }}>Architecture</p>
          <SectionTitle className="text-3xl md:text-4xl lg:text-[52px] font-semibold tracking-tight">Tech &amp; Architecture</SectionTitle>
        </SectionReveal>

        {/* Column headers */}
        <div className="hidden md:flex items-center justify-between px-5 mb-2"
          style={{ borderBottom: "1px solid var(--cx-card-border)", paddingBottom: "8px" }}>
          <div className="flex items-center gap-5 flex-1">
            <div style={{ width: 48, flexShrink: 0 }} />
            <span style={{ fontSize: "10px", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--cx-text-muted)", fontFamily: "var(--font-mono,'JetBrains Mono',monospace)" }}>
              Feature
            </span>
          </div>
          <div className="flex items-center gap-5 ml-4 flex-shrink-0">
            <span style={{ fontSize: "10px", fontWeight: 700, letterSpacing: "0.12em", textTransform: "uppercase", color: "var(--cx-text-muted)", fontFamily: "var(--font-mono,'JetBrains Mono',monospace)", minWidth: 80, textAlign: "right" }}>
              Metric
            </span>
            <div style={{ width: 36 }} />
          </div>
        </div>

        <motion.div
          className="flex flex-col gap-2"
          variants={prefersReduced ? undefined : staggerFastContainer}
          initial={prefersReduced ? false : "hidden"}
          whileInView="visible"
          viewport={{ once: true, amount: 0.1 }}
        >
          {awards.map((item, index) => (
            <motion.div
              key={index}
              variants={prefersReduced ? undefined : staggerFastChild}
            >
              <Link href={item.link}
                className="cx-row group flex items-center justify-between py-4 px-5 rounded-2xl transition-all duration-200"
                style={{ backdropFilter: "blur(12px) saturate(200%)", WebkitBackdropFilter: "blur(12px) saturate(200%)" }}
                onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'rgba(0,0,0,0.04)' }}
                onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = '' }}>

                <div className="flex items-center gap-4 flex-1 min-w-0">
                  {/* Badge — tall enough for multi-word labels */}
                  <motion.div
                    className="cx-stat-card group-hover:!bg-[#1E2A38] group-hover:!border-[#1E2A38] flex-shrink-0 rounded-xl flex items-center justify-center"
                    style={{ backdropFilter: "blur(12px)", WebkitBackdropFilter: "blur(12px)", minWidth: 48, padding: "6px 8px" }}
                    whileHover={prefersReduced ? {} : { scale: 1.05, transition: SPRING.snappy }}
                  >
                    <span className="cx-text-muted group-hover:!text-white" style={{ fontSize: "9px", fontWeight: 700, fontFamily: "var(--font-mono,'JetBrains Mono',monospace)", letterSpacing: "0.04em", textAlign: "center", lineHeight: 1.3 }}>
                      {item.year}
                    </span>
                  </motion.div>
                  <div className="min-w-0">
                    <h3 className="cx-text font-semibold text-base md:text-lg leading-tight">{item.title}</h3>
                    <p className="cx-text-muted text-sm mt-0.5 leading-relaxed line-clamp-1 hidden md:block">{item.organization}</p>
                    <p className="cx-text-muted text-xs mt-0.5 leading-relaxed md:hidden">{item.organization}</p>
                  </div>
                </div>

                <div className="flex items-center gap-4 ml-4 flex-shrink-0">
                  <div className="text-right" style={{ minWidth: 80 }}>
                    <div className="cx-stat-number text-lg md:text-xl font-semibold" style={{ fontVariantNumeric: "tabular-nums" }}>{item.metric}</div>
                    <div className="cx-text-muted text-xs">{item.metricLabel}</div>
                  </div>
                  <motion.div
                    className="cx-arrow-circle group-hover:!bg-[#1E2A38] group-hover:!border-[#1E2A38] w-8 h-8 rounded-full flex items-center justify-center"
                    whileHover={prefersReduced ? {} : { scale: 1.12, transition: SPRING.snappy }}
                  >
                    <ArrowUpRight className="w-3.5 h-3.5 transition-all duration-200 group-hover:!text-white group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
                  </motion.div>
                </div>
              </Link>
            </motion.div>
          ))}
        </motion.div>

      </div>
    </section>
  )
}
