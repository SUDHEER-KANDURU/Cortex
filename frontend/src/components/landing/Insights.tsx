"use client"

import Image from "next/image"
import Link from "next/link"
import { ArrowUpRight } from "lucide-react"
import { SectionTitle } from "@/components/ui/section-title"

const insights = [
  {
    id: 1,
    title: "Why AST Parsing Beats Text Search for Code Understanding",
    excerpt: "How Cortex reads your entire codebase at the syntax-tree level — not with grep — and why it makes all the difference for structural analysis.",
    image: "/images/bg-1.png",
    date: "Dec 2025",
    readTime: "5 min read",
  },
  {
    id: 2,
    title: "Building a Knowledge Graph from Source Code",
    excerpt: "A deep dive into how Cortex maps 241 nodes and 387 relationships from a typical Python repository into Neo4j in under 4 seconds.",
    image: "/images/bg-2.png",
    date: "Nov 2025",
    readTime: "7 min read",
  },
  {
    id: 3,
    title: "Offline-First Engineering Tools — The Case for Zero API Keys",
    excerpt: "Why developer tooling should run on your machine, not in the cloud — and how Cortex achieves production-quality analysis without a single external call.",
    image: "/images/bg-3.png",
    date: "Nov 2025",
    readTime: "4 min read",
  },
]

export function PortfolioInsights() {
  return (
    <section id="insights" className="py-20 md:py-32 border-border border-t-0">
      <div className="max-w-[1280px] mx-auto px-6 md:px-12">
        <div className="flex items-center justify-between mb-12 md:mb-16">
          <SectionTitle className="text-3xl md:text-4xl lg:text-5xl font-semibold tracking-tight">
            Insights
          </SectionTitle>
          <Link href="https://github.com/SUDHEER-KANDURU/cortex" target="_blank" rel="noopener noreferrer"
            className="hidden md:inline-flex items-center gap-2 text-sm transition-colors"
            style={{ color: "#203eec" }}>
            View on GitHub
            <ArrowUpRight className="w-4 h-4" style={{ color: "#203eec" }} />
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 md:gap-8">
          {insights.map((item) => (
            <Link key={item.id} href="https://github.com/SUDHEER-KANDURU/cortex" target="_blank" rel="noopener noreferrer"
              className="group block">
              <article className="h-full">
                <div className="relative aspect-[3/2] overflow-hidden rounded-2xl bg-secondary mb-4">
                  <Image src={item.image || "/placeholder.svg"} alt={item.title} fill
                    className="object-cover transition-transform duration-500 group-hover:scale-105" />
                </div>
                <div className="flex items-center gap-3 text-xs text-muted-foreground mb-3">
                  <span>{item.date}</span>
                  <span>•</span>
                  <span>{item.readTime}</span>
                </div>
                <h3 className="text-lg font-semibold group-hover:text-muted-foreground transition-colors">
                  {item.title}
                </h3>
                <p className="text-sm text-muted-foreground mt-2 leading-relaxed">{item.excerpt}</p>
              </article>
            </Link>
          ))}
        </div>

        <div className="md:hidden mt-8 text-center">
          <Link href="https://github.com/SUDHEER-KANDURU/cortex" target="_blank" rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-6 py-3 text-sm font-medium border rounded-full hover:bg-secondary transition-colors"
            style={{ color: "#203eec", borderColor: "#203eec" }}>
            View on GitHub
            <ArrowUpRight className="w-4 h-4" />
          </Link>
        </div>
      </div>
    </section>
  )
}
