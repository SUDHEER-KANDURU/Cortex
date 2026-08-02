"use client"

import Link from "next/link"
import { ArrowUpRight } from "lucide-react"
import { SectionTitle } from "@/components/ui/section-title"

const insights = [
  {
    id: 1,
    title: "Why AST Parsing Beats Text Search for Code Understanding",
    excerpt: "How Cortex reads your entire codebase at the syntax-tree level — not with grep — and why it makes all the difference for structural analysis.",
    date: "Dec 2025", readTime: "5 min read", tag: "Deep Dive",
    visual: (
      <svg viewBox="0 0 200 90" style={{ width: "100%", height: "90px" }}>
        <rect x="80" y="5"  width="40" height="18" rx="5" fill="rgba(255,255,255,0.85)" opacity="0.9"/>
        <text x="100" y="17" textAnchor="middle" fontSize="7" fill="#060810" fontFamily="monospace" fontWeight="bold">Module</text>
        <line x1="100" y1="23" x2="50"  y2="38" stroke="rgba(255,255,255,0.25)" strokeWidth="1.5"/>
        <line x1="100" y1="23" x2="150" y2="38" stroke="rgba(255,255,255,0.25)" strokeWidth="1.5"/>
        <rect x="20"  y="38" width="60" height="18" rx="5" fill="rgba(255,255,255,0.60)" opacity="0.85"/>
        <text x="50"  y="50" textAnchor="middle" fontSize="7" fill="#060810" fontFamily="monospace" fontWeight="bold">ClassDef</text>
        <rect x="120" y="38" width="60" height="18" rx="5" fill="rgba(255,255,255,0.60)" opacity="0.85"/>
        <text x="150" y="50" textAnchor="middle" fontSize="7" fill="#060810" fontFamily="monospace" fontWeight="bold">FuncDef</text>
        <line x1="50"  y1="56" x2="30" y2="70" stroke="rgba(255,255,255,0.18)" strokeWidth="1.2"/>
        <line x1="50"  y1="56" x2="70" y2="70" stroke="rgba(255,255,255,0.18)" strokeWidth="1.2"/>
        <rect x="10"  y="70" width="40" height="14" rx="4" fill="rgba(255,255,255,0.35)" opacity="0.75"/>
        <text x="30"  y="80" textAnchor="middle" fontSize="6" fill="#060810" fontFamily="monospace">Assign</text>
        <rect x="55"  y="70" width="35" height="14" rx="4" fill="rgba(255,255,255,0.35)" opacity="0.75"/>
        <text x="72"  y="80" textAnchor="middle" fontSize="6" fill="#060810" fontFamily="monospace">Return</text>
      </svg>
    ),
  },
  {
    id: 2,
    title: "Building a Knowledge Graph from Source Code",
    excerpt: "A deep dive into how Cortex maps 241 nodes and 387 relationships from a typical Python repository into Neo4j in under 4 seconds.",
    date: "Nov 2025", readTime: "7 min read", tag: "Architecture",
    visual: (
      <svg viewBox="0 0 200 90" style={{ width: "100%", height: "90px" }}>
        {[[100,45],[50,20],[150,20],[30,70],[80,75],[140,70],[170,45]].map(([cx,cy], i) => (
          <circle key={i} cx={cx} cy={cy} r={i===0 ? 12 : 7}
            fill={i===0 ? "var(--primary)" : i<=2 ? "rgba(0,229,168,0.55)" : "rgba(0,229,168,0.30)"}
            opacity="0.9" />
        ))}
        {[[0,1],[0,2],[0,3],[0,4],[0,5],[0,6],[1,3],[2,5]].map(([a,b], i) => {
          const pts = [[100,45],[50,20],[150,20],[30,70],[80,75],[140,70],[170,45]]
          return <line key={i} x1={pts[a][0]} y1={pts[a][1]} x2={pts[b][0]} y2={pts[b][1]}
            stroke="rgba(0,229,168,0.20)" strokeWidth="1.2" strokeDasharray="3 2" />
        })}
        <text x="100" y="83" textAnchor="middle" fontSize="7" fill="var(--text-muted)" fontFamily="monospace" fontWeight="600">
          241 nodes · 387 edges
        </text>
      </svg>
    ),
  },
  {
    id: 3,
    title: "Offline-First Engineering Tools — The Case for Zero API Keys",
    excerpt: "Why developer tooling should run on your machine, not in the cloud — and how Cortex achieves production-quality analysis without a single external call.",
    date: "Nov 2025", readTime: "4 min read", tag: "Philosophy",
    visual: (
      <svg viewBox="0 0 200 90" style={{ width: "100%", height: "90px" }}>
        <rect x="60" y="10" width="80" height="55" rx="8" fill="rgba(255,255,255,0.05)" stroke="rgba(255,255,255,0.15)" strokeWidth="1.5"/>
        <rect x="72" y="22" width="56" height="32" rx="4" fill="rgba(255,255,255,0.07)"/>
        <text x="100" y="33" textAnchor="middle" fontSize="7" fill="var(--text)" fontFamily="monospace" fontWeight="700">Your Machine</text>
        <text x="100" y="44" textAnchor="middle" fontSize="6" fill="var(--text-muted)" fontFamily="monospace">Cortex Engine</text>
        <text x="100" y="54" textAnchor="middle" fontSize="6" fill="var(--text-muted)" fontFamily="monospace">Neo4j · Redis</text>
        <rect x="85"  y="65" width="30" height="5" rx="2.5" fill="rgba(255,255,255,0.10)"/>
        <circle cx="155" cy="30" r="16" fill="rgba(239,83,80,0.06)" stroke="rgba(239,83,80,0.25)" strokeWidth="1.5"/>
        <text x="155"  y="28" textAnchor="middle" fontSize="9" fill="rgba(239,83,80,0.65)">☁</text>
        <line x1="143" y1="18" x2="167" y2="42" stroke="rgba(239,83,80,0.55)" strokeWidth="2" strokeLinecap="round"/>
        <text x="100" y="82" textAnchor="middle" fontSize="7" fill="var(--text-muted)" fontFamily="monospace" fontWeight="600">0 external API calls</text>
      </svg>
    ),
  },
]

export function PortfolioInsights() {
  return (
    <section id="insights" className="py-20 md:py-32"
      style={{ borderTop: "1px solid var(--cx-card-border)", background: "var(--cx-section-bg)", backdropFilter: "blur(20px) saturate(200%)", WebkitBackdropFilter: "blur(20px) saturate(200%)" }}>
      <div className="max-w-[1280px] mx-auto px-6 md:px-12">
        <div className="flex items-center justify-between mb-12 md:mb-16">
          <div data-reveal="up">
            <p className="cx-eyebrow" style={{ fontSize: "10px", fontWeight: 700, letterSpacing: "0.16em", textTransform: "uppercase", fontFamily: "var(--font-mono,'JetBrains Mono',monospace)", marginBottom: "10px" }}>Writing</p>
            <SectionTitle className="text-3xl md:text-4xl lg:text-[52px] font-semibold tracking-tight">Insights</SectionTitle>
          </div>
          <Link href="https://github.com/SUDHEER-KANDURU/cortex" target="_blank" rel="noopener noreferrer"
            className="cx-link hidden md:inline-flex items-center gap-2 text-sm font-medium transition-all duration-200 hover:gap-3">
            View on GitHub <ArrowUpRight className="w-4 h-4" />
          </Link>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-5 md:gap-6" data-stagger>
          {insights.map((item) => (
            <Link key={item.id} href="https://github.com/SUDHEER-KANDURU/cortex" target="_blank" rel="noopener noreferrer" className="group block">
              <article className="cx-card h-full rounded-2xl overflow-hidden transition-all duration-400 hover:-translate-y-2"
                data-spotlight
                style={{ backdropFilter: "blur(8px) saturate(180%)", WebkitBackdropFilter: "blur(8px) saturate(180%)" }}>
                <div className="cx-visual-bg" style={{ height: "110px", overflow: "hidden", borderBottom: "1px solid var(--cx-card-border)", backdropFilter: "blur(8px)", WebkitBackdropFilter: "blur(8px)", padding: "10px", display: "flex", alignItems: "center", justifyContent: "center" }}>
                  {item.visual}
                </div>
                <div className="p-5">
                  <div className="flex items-center justify-between mb-3">
                    <span className="cx-pill" style={{ fontSize: "9px", fontWeight: 700, letterSpacing: "0.1em", textTransform: "uppercase", padding: "3px 10px", borderRadius: "100px", backdropFilter: "blur(12px)", WebkitBackdropFilter: "blur(12px)", fontFamily: "var(--font-mono,'JetBrains Mono',monospace)" }}>
                      {item.tag}
                    </span>
                    <div className="cx-text-muted flex items-center gap-2 text-xs">
                      <span>{item.date}</span><span>·</span><span>{item.readTime}</span>
                    </div>
                  </div>
                  <h3 className="cx-text text-base font-semibold leading-snug transition-opacity duration-200 group-hover:opacity-60">{item.title}</h3>
                  <p className="cx-text-muted text-sm mt-2 leading-relaxed">{item.excerpt}</p>
                  <div className="cx-link flex items-center gap-1.5 mt-4 text-xs font-semibold transition-all duration-200 group-hover:gap-2.5">
                    Read more <ArrowUpRight className="w-3 h-3" />
                  </div>
                </div>
              </article>
            </Link>
          ))}
        </div>

        <div className="md:hidden mt-8 text-center">
          <Link href="https://github.com/SUDHEER-KANDURU/cortex" target="_blank" rel="noopener noreferrer"
            className="cx-link cx-row inline-flex items-center gap-2 px-6 py-3 text-sm font-medium rounded-full transition-colors">
            View on GitHub <ArrowUpRight className="w-4 h-4" />
          </Link>
        </div>
      </div>
    </section>
  )
}

