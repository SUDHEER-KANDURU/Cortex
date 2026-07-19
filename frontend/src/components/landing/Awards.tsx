"use client"

import { ArrowUpRight } from "lucide-react"
import Link from "next/link"
import { SectionTitle } from "@/components/ui/section-title"

const awards = [
  { title: "AST-Level Parsing",       year: "Core",      metric: "100%",  metricLabel: "structural",   organization: "Full abstract syntax tree analysis — not just text grep. Every symbol, import, and call extracted.",                       link: "#about" },
  { title: "Neo4j Knowledge Graph",   year: "Core",      metric: "241+",  metricLabel: "nodes / repo", organization: "241 nodes and 387 relationships mapped per average repository into a queryable graph.",                                  link: "#about" },
  { title: "Zero API Keys Required",  year: "Principle", metric: "$0",    metricLabel: "cloud cost",   organization: "Runs entirely on-device — no OpenAI, no Gemini, no cloud costs. Pure local reasoning.",                                  link: "#about" },
  { title: "6 Artifact Types",        year: "Output",    metric: "6",     metricLabel: "per scan",     organization: "Architecture diagrams, learning paths, API specs, interview prep, vibe code reports & onboarding guides.",               link: "/dashboard" },
  { title: "Celery Async Pipeline",   year: "Infra",     metric: "async", metricLabel: "non-blocking", organization: "Background workers handle large repos without blocking the UI. Real-time job status polling.",                            link: "#about" },
  { title: "Docker-First Deployment", year: "DevOps",    metric: "1 cmd", metricLabel: "full stack",   organization: "Single docker-compose up spins database, workers, API, and frontend. Zero config friction.",                             link: "https://github.com/SUDHEER-KANDURU/cortex" },
]

export function PortfolioAwards() {
  return (
    <section id="awards" className="py-20 md:py-32 md:pt-0 md:pb-0"
      style={{
        borderTop: "1px solid rgba(255,255,255,0.6)",
        background: "rgba(255,255,255,0.52)",
        backdropFilter: "blur(8px) saturate(170%)",
        WebkitBackdropFilter: "blur(8px) saturate(170%)",
        boxShadow: "inset 0 1px 0 rgba(255,255,255,0.9)",
      }}>
      <div className="max-w-[1280px] mx-auto px-6 md:px-12">
        <div className="mb-12 md:mb-16" data-reveal="up">
          <p style={{
            fontSize: "10px", fontWeight: 700, letterSpacing: "0.16em",
            textTransform: "uppercase", color: "rgba(0,0,0,0.35)",
            fontFamily: "var(--font-mono,'Fira Code',monospace)", marginBottom: "10px",
          }}>
            Architecture
          </p>
          <SectionTitle className="text-3xl md:text-4xl lg:text-[52px] font-semibold tracking-tight">
            Tech &amp; Architecture
          </SectionTitle>
        </div>
        <div className="flex flex-col gap-3" data-stagger>
          {awards.map((item, index) => (
            <Link key={index} href={item.link}
              className="group flex items-center justify-between p-5 md:p-6 rounded-2xl transition-all duration-350"
              style={{
                background: "rgba(255,255,255,0.45)",
                backdropFilter: "blur(12px) saturate(160%)",
                WebkitBackdropFilter: "blur(12px) saturate(160%)",
                border: "1px solid rgba(255,255,255,0.7)",
                boxShadow: "0 2px 12px rgba(0,0,0,0.04), inset 0 1px 0 rgba(255,255,255,0.9)",
              }}
              onMouseEnter={e => {
                const el = e.currentTarget as HTMLElement
                el.style.background = "rgba(255,255,255,0.75)"
                el.style.borderColor = "rgba(255,255,255,1)"
                el.style.boxShadow = "0 8px 32px rgba(0,0,0,0.08), inset 0 1px 0 rgba(255,255,255,1)"
                el.style.transform = "translateX(4px)"
              }}
              onMouseLeave={e => {
                const el = e.currentTarget as HTMLElement
                el.style.background = "rgba(255,255,255,0.45)"
                el.style.borderColor = "rgba(255,255,255,0.7)"
                el.style.boxShadow = "0 2px 12px rgba(0,0,0,0.04), inset 0 1px 0 rgba(255,255,255,0.9)"
                el.style.transform = "none"
              }}>

              <div className="flex items-center gap-5 flex-1 min-w-0">
                <div style={{
                  width: "40px", height: "40px", borderRadius: "12px", flexShrink: 0,
                  background: "rgba(255,255,255,0.7)",
                  backdropFilter: "blur(12px)",
                  WebkitBackdropFilter: "blur(12px)",
                  border: "1px solid rgba(255,255,255,0.9)",
                  boxShadow: "0 2px 8px rgba(0,0,0,0.06), inset 0 1px 0 rgba(255,255,255,1)",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  transition: "all 0.3s ease",
                }} className="group-hover:scale-110 group-hover:bg-black">
                  <span style={{ fontSize: "9px", fontWeight: 700, color: "#666", fontFamily: "var(--font-mono,'Fira Code',monospace)", letterSpacing: "0.04em" }}
                    className="group-hover:!text-white">
                    {item.year}
                  </span>
                </div>
                <div className="min-w-0">
                  <h3 className="font-semibold text-lg md:text-xl">{item.title}</h3>
                  <p className="text-sm text-muted-foreground mt-0.5 leading-relaxed">{item.organization}</p>
                </div>
              </div>

              <div className="flex items-center gap-5 ml-4 flex-shrink-0">
                <div className="hidden md:block text-right">
                  <div className="text-xl font-semibold" style={{ color: "#111", fontVariantNumeric: "tabular-nums" }}>
                    {item.metric}
                  </div>
                  <div className="text-xs text-muted-foreground">{item.metricLabel}</div>
                </div>
                <div style={{
                  width: "36px", height: "36px", borderRadius: "50%",
                  border: "1px solid rgba(0,0,0,0.12)",
                  display: "flex", alignItems: "center", justifyContent: "center",
                  transition: "all 0.3s ease",
                }} className="group-hover:bg-black group-hover:border-black">
                  <ArrowUpRight className="w-4 h-4 transition-all duration-300 group-hover:text-white group-hover:translate-x-0.5 group-hover:-translate-y-0.5"
                    style={{ color: "#888" }} />
                </div>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </section>
  )
}
