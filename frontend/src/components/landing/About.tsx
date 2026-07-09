"use client"

import { SectionTitle } from "@/components/ui/section-title"

const skills = [
  "AST Parsing", "Neo4j Graph DB", "FastAPI", "Python 3.12",
  "Celery Workers", "PostgreSQL", "Redis", "React Flow",
  "Next.js 14", "Architecture Analysis", "Knowledge Graphs", "LLM-Free",
]

const stats = [
  { value: "6",    label: "Artifact Types"     },
  { value: "0",    label: "API Keys Required"   },
  { value: "100%", label: "Offline Capable"     },
]

export function PortfolioAbout() {
  return (
    <section id="about" className="py-20 border-border border-t-0 md:py-10 md:pb-32 md:pt-32">
      <div className="max-w-[1280px] mx-auto px-6 md:px-12">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 lg:gap-20">
          <div>
            <SectionTitle className="text-3xl md:text-4xl lg:text-5xl font-semibold tracking-tight text-balance">
              Bridging Static Code & Structural Understanding
            </SectionTitle>
            <p className="mt-6 text-muted-foreground leading-relaxed">
              Cortex is an Engineering Reasoning Engine built for developers who want to deeply understand any codebase they work with. It reads your repository at the AST level, constructs a rich knowledge graph in Neo4j, and generates artifacts that explain the system — not just describe it.
            </p>
            <p className="mt-4 text-muted-foreground leading-relaxed">
              Built by Sudheer Kanduru at SRMIST Chennai, Cortex runs entirely on your machine. No API keys, no cloud billing, no data leaving your environment. Just deep structural analysis at your fingertips.
            </p>
          </div>

          <div>
            <div>
              <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground mb-4">Tech Stack</h3>
              <div className="flex flex-wrap gap-2">
                {skills.map((skill) => (
                  <span key={skill}
                    className="px-4 py-2 text-sm font-medium border border-border rounded-full hover:bg-secondary transition-colors cursor-default">
                    {skill}
                  </span>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4 mt-12">
              {stats.map((stat) => (
                <div key={stat.label} className="text-center p-4 bg-secondary rounded-2xl">
                  <div className="text-2xl md:text-3xl font-semibold">{stat.value}</div>
                  <div className="text-xs text-muted-foreground mt-1">{stat.label}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}
