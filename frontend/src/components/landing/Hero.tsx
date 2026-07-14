"use client"

import Link from "next/link"
import { ArrowDown } from "lucide-react"
import { useEffect, useRef, useState } from "react"
import dynamic from "next/dynamic"

const RepoTree = dynamic(() => import("@/features/tree/RepoTree"), {
  ssr: false,
  loading: () => <div style={{ width: "100%", height: "100%" }} />,
})

export function PortfolioHero() {
  const titleText = "Understand any codebase with AI reasoning"
  const words = titleText.split(" ")

  // 0→1 progress passed into the 3D tree — driven by scroll through the pin zone
  const progressRef = useRef(0)
  const spacerRef   = useRef<HTMLDivElement>(null)
  const [isDesktop, setIsDesktop] = useState(false)

  useEffect(() => {
    const check = () => setIsDesktop(window.innerWidth >= 768)
    check()
    window.addEventListener("resize", check)

    const handleScroll = () => {
      const spacer = spacerRef.current
      if (!spacer) return
      const top    = spacer.getBoundingClientRect().top + window.scrollY  // absolute top
      const height = spacer.offsetHeight - window.innerHeight              // scrollable distance
      const raw    = (window.scrollY - top) / height
      progressRef.current = Math.max(0, Math.min(1, raw))
    }

    handleScroll()
    window.addEventListener("scroll", handleScroll, { passive: true })
    return () => {
      window.removeEventListener("resize", check)
      window.removeEventListener("scroll", handleScroll)
    }
  }, [])

  return (
    <>
      {/*
        Tall spacer — this creates the scroll runway.
        300vh gives enough distance for progress 0→1 to play the full tree
        reveal without rushing. The sticky inner div locks the hero in view.
      */}
      <div ref={spacerRef} style={{ height: "300vh", position: "relative" }}>
        <div style={{
          position: "sticky",
          top: 0,
          height: "100vh",
          overflow: "hidden",
          paddingTop: "80px", // clear fixed header
        }}>
          <div className="max-w-[1280px] mx-auto px-6 md:px-12 h-full grid grid-cols-1 md:grid-cols-2 gap-8 items-center">

            {/* ── Left: hero copy ── */}
            <div>
              <p className="text-muted-foreground mb-6 text-lg font-normal">
                Cortex — Engineering Reasoning Engine
              </p>

              <h1 className="text-4xl sm:text-5xl lg:text-[68px] font-semibold tracking-tight leading-[1] text-balance">
                {words.map((word, index) => (
                  <span
                    key={index}
                    className={`hero-word py-1 font-mono font-normal text-4xl md:text-5xl ${word === "AI" ? "ai-gradient-word" : ""}`}
                    style={{
                      display: "inline-block",
                      animationDelay: `${index * 0.1}s`,
                      marginRight: index < words.length - 1 ? "0.25em" : "0",
                      ...(word === "AI" ? {
                        background: "linear-gradient(135deg,#ff006e 0%,#8b5cf6 33%,#203eec 66%,#00d4ff 100%)",
                        WebkitBackgroundClip: "text",
                        WebkitTextFillColor: "transparent",
                        backgroundClip: "text",
                        filter: "drop-shadow(0 0 20px rgba(255,0,110,.3)) drop-shadow(0 0 30px rgba(139,92,246,.3))",
                      } : {}),
                    }}
                  >
                    {word}
                  </span>
                ))}
              </h1>

              <p className="mt-6 max-w-md leading-relaxed text-base text-zinc-500">
                Paste any GitHub URL. Cortex scans your repository, builds a Neo4j knowledge
                graph, and generates architecture diagrams, learning paths, and interview
                prep — fully offline, zero API keys.
              </p>

              <div className="flex flex-row flex-wrap items-start gap-4 mt-8">
                <Link href="/dashboard"
                  className="inline-flex items-center justify-center px-7 py-3.5 text-sm font-medium text-white rounded-full transition-all relative overflow-hidden group"
                  style={{ background: "linear-gradient(135deg,#203eec 0%,#00d4ff 100%)", boxShadow: "0 4px 20px rgba(32,62,236,.3)" }}
                  onMouseEnter={e => { e.currentTarget.style.boxShadow = "0 8px 30px rgba(32,62,236,.5),0 0 40px rgba(0,212,255,.3)" }}
                  onMouseLeave={e => { e.currentTarget.style.boxShadow = "0 4px 20px rgba(32,62,236,.3)" }}
                >
                  Analyze a Repository
                </Link>
                <Link href="#works"
                  className="inline-flex items-center gap-2 px-7 py-3.5 text-sm font-medium transition-colors"
                  style={{ color: "#203eec" }}>
                  See Capabilities
                  <ArrowDown className="w-4 h-4" />
                </Link>
              </div>

              <p className="mt-8 text-xs tracking-widest uppercase"
                style={{ color: "rgba(0,0,0,0.25)" }}>
                Scroll to grow the repository tree →
              </p>
            </div>

            {/* ── Right: 3D scroll-driven repository tree ── */}
            {/* Always mounted so the canvas exists; hidden on mobile via opacity */}
            <div style={{
              height: "100%",
              position: "relative",
              opacity: isDesktop ? 1 : 0,
              pointerEvents: isDesktop ? "auto" : "none",
            }}>
              {/* Dark card wrapper so nodes are visible on the white landing page */}
              <div style={{
                position: "absolute",
                inset: "16px 0",
                borderRadius: "20px",
                background: "linear-gradient(135deg, #0a0a1a 0%, #0d0d2a 100%)",
                boxShadow: "0 8px 48px rgba(76,29,149,0.25), 0 2px 8px rgba(0,0,0,0.15)",
                overflow: "hidden",
              }}>
                {/* Top label */}
                <div style={{
                  position: "absolute", top: "16px", left: "50%",
                  transform: "translateX(-50%)",
                  zIndex: 10, pointerEvents: "none",
                  display: "flex", alignItems: "center", gap: "8px",
                  background: "rgba(255,255,255,0.06)",
                  backdropFilter: "blur(8px)",
                  border: "1px solid rgba(255,255,255,0.1)",
                  borderRadius: "100px",
                  padding: "5px 14px",
                  whiteSpace: "nowrap",
                }}>
                  <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: "#4C1D95", boxShadow: "0 0 8px #4C1D95", display: "inline-block" }} />
                  <span style={{ fontSize: "10px", fontWeight: 600, letterSpacing: "0.12em", textTransform: "uppercase", color: "rgba(255,255,255,0.6)" }}>
                    Live Repository Graph
                  </span>
                </div>

                <RepoTree progress={progressRef} />

                {/* Bottom fade */}
                <div style={{
                  position: "absolute", bottom: 0, left: 0, right: 0,
                  height: "60px",
                  background: "linear-gradient(to top, #0a0a1a 0%, transparent 100%)",
                  pointerEvents: "none",
                }} />
              </div>
            </div>

          </div>
        </div>
      </div>
    </>
  )
}
