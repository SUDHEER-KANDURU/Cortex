"use client"

import { ArrowUpRight } from "lucide-react"
import Link from "next/link"
import { SectionTitle } from "@/components/ui/section-title"

const awards = [
  { title: "AST-Level Parsing",       year: "Core",      metric: "100%",  metricLabel: "structural",   organization: "Full abstract syntax tree analysis — not just text grep. Every symbol, import, and call extracted.",                     link: "#about" },
  { title: "Neo4j Knowledge Graph",   year: "Core",      metric: "241+",  metricLabel: "nodes / repo", organization: "241 nodes and 387 relationships mapped per average repository into a queryable graph.",                                link: "#about" },
  { title: "Zero API Keys Required",  year: "Principle", metric: "$0",    metricLabel: "cloud cost",   organization: "Runs entirely on-device — no OpenAI, no Gemini, no cloud costs. Pure local reasoning.",                                link: "#about" },
  { title: "6 Artifact Types",        year: "Output",    metric: "6",     metricLabel: "per scan",     organization: "Architecture diagrams, learning paths, API specs, interview prep, vibe code reports & onboarding guides.",             link: "/dashboard" },
  { title: "Celery Async Pipeline",   year: "Infra",     metric: "async", metricLabel: "non-blocking", organization: "Background workers handle large repos without blocking the UI. Real-time job status polling.",                          link: "#about" },
  { title: "Docker-First Deployment", year: "DevOps",    metric: "1 cmd", metricLabel: "full stack",   organization: "Single docker-compose up spins database, workers, API, and frontend. Zero config friction.",                           link: "https://github.com/SUDHEER-KANDURU/cortex" },
]

export function PortfolioAwards() {
  return (
    <section id="awards" className="py-20 md:py-32 md:pt-0 md:pb-0"
      style={{ borderTop: "1px solid var(--cx-card-border)", background: "var(--cx-section-bg)", backdropFilter: "blur(20px) saturate(200%)", WebkitBackdropFilter: "blur(20px) saturate(200%)" }}>
      <div className="max-w-[1280px] mx-auto px-6 md:px-12">
        <div className="mb-12 md:mb-16" data-reveal="up">
          <p className="cx-eyebrow" style={{ fontSize: "10px", fontWeight: 700, letterSpacing: "0.16em", textTransform: "uppercase", fontFamily: "var(--font-mono,'JetBrains Mono',monospace)", marginBottom: "10px" }}>Architecture</p>
          <SectionTitle className="text-3xl md:text-4xl lg:text-[52px] font-semibold tracking-tight">Tech &amp; Architecture</SectionTitle>
        </div>
        <div className="flex flex-col gap-3" data-stagger>
          {awards.map((item, index) => (
            <Link key={index} href={item.link}
              className="cx-row group flex items-center justify-between p-5 md:p-6 rounded-2xl transition-all duration-300"
              style={{ backdropFilter: "blur(12px) saturate(200%)", WebkitBackdropFilter: "blur(12px) saturate(200%)" }}
              onMouseEnter={e => { (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.04)' }}
              onMouseLeave={e => { (e.currentTarget as HTMLElement).style.background = '' }}>

              <div className="flex items-center gap-5 flex-1 min-w-0">
                <div className="cx-stat-card group-hover:!bg-black group-hover:!border-black flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center transition-all duration-300 group-hover:scale-110"
                  style={{ backdropFilter: "blur(12px)", WebkitBackdropFilter: "blur(12px)" }}>
                  <span className="cx-text-muted group-hover:!text-white" style={{ fontSize: "9px", fontWeight: 700, fontFamily: "var(--font-mono,'JetBrains Mono',monospace)", letterSpacing: "0.04em" }}>
                    {item.year}
                  </span>
                </div>
                <div className="min-w-0">
                  <h3 className="cx-text font-semibold text-lg md:text-xl">{item.title}</h3>
                  <p className="cx-text-muted text-sm mt-0.5 leading-relaxed">{item.organization}</p>
                </div>
              </div>

              <div className="flex items-center gap-5 ml-4 flex-shrink-0">
                <div className="hidden md:block text-right">
                  <div className="cx-stat-number text-xl font-semibold" style={{ fontVariantNumeric: "tabular-nums" }}>{item.metric}</div>
                  <div className="cx-text-muted text-xs">{item.metricLabel}</div>
                </div>
                <div className="cx-arrow-circle group-hover:!bg-black group-hover:!border-black w-9 h-9 rounded-full flex items-center justify-center transition-all duration-300">
                  <ArrowUpRight className="w-4 h-4 transition-all duration-300 group-hover:!text-white group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
                </div>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </section>
  )
}
