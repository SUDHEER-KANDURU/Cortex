"use client"

import Image from "next/image"
import Link from "next/link"
import { ArrowUpRight } from "lucide-react"
import { SectionTitle } from "@/components/ui/section-title"

const works = [
  {
    id: 1,
    title: "Architecture Diagram Generator",
    category: "Code Intelligence",
    description: "Auto-generates Mermaid flowcharts showing every module, dependency, and service boundary in your codebase.",
    image: "/images/work-onboarding.png",
    tags: ["AST Parsing", "Neo4j", "Mermaid"],
  },
  {
    id: 2,
    title: "Learning Path Builder",
    category: "Developer Education",
    description: "Identifies every concept and pattern in your repository and creates a personalised curriculum ordered from fundamentals to advanced.",
    image: "/images/work-fashion.png",
    tags: ["Knowledge Graph", "NLP", "FastAPI"],
  },
  {
    id: 3,
    title: "Interview Prep Engine",
    category: "Career Tools",
    description: "Generates 10 technical questions grounded in your actual project code with model answers. Walk into any interview prepared.",
    image: "/images/work-tasks.png",
    tags: ["Graph Queries", "Python", "Celery"],
  },
  {
    id: 4,
    title: "Vibe Code Detector",
    category: "Code Quality",
    description: "Flags AI-generated anti-patterns — missing error handling, duplicate logic, inconsistent naming — and explains exactly how to fix each one.",
    image: "/images/work-crypto.png",
    tags: ["Static Analysis", "LLM-free", "Neo4j"],
  },
]

export function PortfolioSelectedWorks() {
  return (
    <section id="works" className="py-20 md:py-10 md:pt-32 pb-4">
      <div className="max-w-[1280px] mx-auto px-6 md:px-12">
        <div className="flex items-center justify-between mb-12 md:mb-16">
          <SectionTitle className="text-3xl md:text-4xl lg:text-5xl font-semibold tracking-tight">
            Capabilities
          </SectionTitle>
          <Link href="/dashboard"
            className="hidden md:inline-flex items-center gap-2 text-sm transition-colors"
            style={{ color: "#203eec" }}>
            Launch App
            <ArrowUpRight className="w-4 h-4" style={{ color: "#203eec" }} />
          </Link>
        </div>

        <div className="relative">
          {works.map((work, index) => (
            <div key={work.id} className="sticky" style={{ top: `${70 + index * 0}px`, zIndex: index + 1 }}>
              <Link href="/dashboard" className="group block pt-10">
                <article className="overflow-hidden rounded-2xl md:rounded-3xl border border-border bg-card transition-all duration-300 hover:shadow-lg hover:-translate-y-1">
                  <div className="relative aspect-[2/1] overflow-hidden bg-secondary">
                    <Image src={work.image || "/placeholder.svg"} alt={work.title} fill
                      className="object-cover transition-transform duration-500 group-hover:scale-105" />
                  </div>
                  <div className="p-3 md:p-3">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <h3 className="text-lg md:text-xl font-semibold">{work.title}</h3>
                        <p className="text-sm text-muted-foreground mt-1">{work.description}</p>
                      </div>
                      <ArrowUpRight className="w-5 h-5 opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0 mt-1"
                        style={{ color: "#203eec" }} />
                    </div>
                    <div className="flex flex-wrap gap-2 mt-4">
                      {work.tags.map((tag) => (
                        <span key={tag} className="px-3 py-1 text-xs font-medium bg-secondary text-secondary-foreground rounded-full">
                          {tag}
                        </span>
                      ))}
                    </div>
                  </div>
                </article>
              </Link>
            </div>
          ))}
        </div>

        <div className="md:hidden mt-8 text-center">
          <Link href="/dashboard"
            className="inline-flex items-center gap-2 px-6 py-3 text-sm font-medium border rounded-full hover:bg-secondary transition-colors"
            style={{ color: "#203eec", borderColor: "#203eec" }}>
            Launch App
            <ArrowUpRight className="w-4 h-4" />
          </Link>
        </div>
      </div>
    </section>
  )
}
