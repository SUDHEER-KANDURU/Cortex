"use client"

import { ArrowUpRight } from "lucide-react"
import Link from "next/link"
import { SectionTitle } from "@/components/ui/section-title"

const awards = [
  { title: "AST-Level Parsing",            year: "Core",      organization: "Full abstract syntax tree analysis — not just text grep",               link: "#about" },
  { title: "Neo4j Knowledge Graph",        year: "Core",      organization: "256+ nodes and relationships mapped per average repository",            link: "#about" },
  { title: "Zero API Keys Required",       year: "Principle", organization: "Runs entirely on-device — no OpenAI, no Gemini, no cloud costs",       link: "#about" },
  { title: "6 Artifact Types",             year: "Output",    organization: "Architecture diagrams, learning paths, API specs, interview prep & more", link: "/dashboard" },
  { title: "Celery Async Pipeline",        year: "Infra",     organization: "Background workers handle large repos without blocking the UI",          link: "#about" },
  { title: "Docker-First Deployment",      year: "DevOps",    organization: "Single docker-compose up — database, workers, API, frontend",           link: "https://github.com/SUDHEER-KANDURU/cortex" },
]

export function PortfolioAwards() {
  return (
    <section id="awards" className="py-20 md:py-32 border-border border-t-0 md:pt-0 md:pb-0">
      <div className="max-w-[1280px] mx-auto px-6 md:px-12">
        <SectionTitle className="text-3xl md:text-4xl lg:text-5xl font-semibold tracking-tight mb-12 md:mb-16">
          Tech &amp; Architecture
        </SectionTitle>

        <div className="flex flex-col gap-4">
          {awards.map((item, index) => (
            <Link key={index} href={item.link}
              className="group flex items-center justify-between p-5 md:p-6 border border-border rounded-2xl hover:bg-secondary/50 transition-all hover:border-foreground/20">
              <div className="flex items-center gap-6 flex-1">
                <div className="flex-1">
                  <h3 className="font-semibold text-xl md:text-2xl">{item.title}</h3>
                  <p className="text-sm text-muted-foreground mt-1">{item.organization}</p>
                </div>
                <span className="text-sm text-muted-foreground font-medium">{item.year}</span>
              </div>
              <ArrowUpRight className="w-8 h-8 md:w-10 md:h-10 ml-6 text-muted-foreground transition-all group-hover:translate-x-1"
                strokeWidth={1} style={{ color: "#203eec" }} />
            </Link>
          ))}
        </div>
      </div>
    </section>
  )
}
