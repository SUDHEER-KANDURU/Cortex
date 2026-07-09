"use client"

import Link from "next/link"
import Image from "next/image"
import { ArrowDown } from "lucide-react"
import { useEffect, useState } from "react"

export function PortfolioHero() {
  const titleText = "Understand any codebase with AI reasoning"
  const words = titleText.split(" ")
  const [maskReveal, setMaskReveal] = useState(0)
  const [opacity, setOpacity]       = useState(0)
  const [isDesktop, setIsDesktop]   = useState(false)

  useEffect(() => {
    const check = () => setIsDesktop(window.innerWidth >= 768)
    check()
    window.addEventListener("resize", check)
    const handleScroll = () => {
      const s = window.scrollY
      const max = 500
      setMaskReveal(Math.min(100, (s / max) * 100))
      setOpacity(Math.min(1, s / max))
    }
    handleScroll()
    window.addEventListener("scroll", handleScroll)
    return () => {
      window.removeEventListener("resize", check)
      window.removeEventListener("scroll", handleScroll)
    }
  }, [])

  return (
    <section className="min-h-screen flex flex-col justify-center pt-20 relative overflow-hidden">
      {/* Animated orb */}
      <div className="absolute -right-32 md:-right-48 top-32 md:top-40 w-[500px] h-[500px] md:w-[750px] md:h-[750px] pointer-events-none animate-orb-rotate -z-10 scale-125">
        <Image src="/images/orb.png" alt="" width={750} height={750} className="w-full h-full" priority />
      </div>

      <div className="max-w-[1280px] mx-auto px-6 md:px-12 py-20 md:py-32 md:pb-4 pb-4 pt-4 md:pt-32">
        <div className="max-w-4xl">
          <p className="text-muted-foreground mb-6 text-lg font-normal">
            Cortex — Engineering Reasoning Engine
          </p>

          <h1 className="text-5xl sm:text-6xl lg:text-[96px] font-semibold tracking-tight leading-[1] text-balance md:text-9xl">
            {words.map((word, index) => (
              <span
                key={index}
                className={`hero-word my-0 py-2 font-mono font-normal text-5xl md:text-7xl ${word === "AI" ? "ai-gradient-word" : ""}`}
                style={{
                  animationDelay: `${index * 0.1}s`,
                  marginRight: index < words.length - 1 ? "0.25em" : "0",
                  ...(word === "AI" ? {
                    background: "linear-gradient(135deg, #ff006e 0%, #8b5cf6 33%, #203eec 66%, #00d4ff 100%)",
                    WebkitBackgroundClip: "text",
                    WebkitTextFillColor: "transparent",
                    backgroundClip: "text",
                    filter: "drop-shadow(0 0 20px rgba(255,0,110,0.3)) drop-shadow(0 0 30px rgba(139,92,246,0.3)) drop-shadow(0 0 40px rgba(0,212,255,0.2))",
                  } : {}),
                }}
              >
                {word}
              </span>
            ))}
          </h1>

          <p className="mt-8 max-w-xl leading-relaxed text-left text-lg text-zinc-500 ml-0">
            Paste any GitHub URL. Cortex scans your repository, builds a Neo4j knowledge graph, and generates architecture diagrams, learning paths, and interview prep — fully offline, zero API keys.
          </p>

          <div className="flex flex-row items-start gap-4 mt-10">
            <Link href="/dashboard"
              className="inline-flex items-center justify-center px-8 py-4 text-base font-medium text-white rounded-full transition-all relative overflow-hidden group"
              style={{ background: "linear-gradient(135deg, #203eec 0%, #00d4ff 100%)", boxShadow: "0 4px 20px rgba(32,62,236,0.3)" }}
              onMouseEnter={(e) => { e.currentTarget.style.boxShadow = "0 8px 30px rgba(32,62,236,0.5), 0 0 40px rgba(0,212,255,0.3)" }}
              onMouseLeave={(e) => { e.currentTarget.style.boxShadow = "0 4px 20px rgba(32,62,236,0.3)" }}
            >
              Analyze a Repository
            </Link>
            <Link href="#works"
              className="inline-flex items-center gap-2 px-8 py-4 text-base font-medium transition-colors"
              style={{ color: "#203eec" }}>
              See Capabilities
              <ArrowDown className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </div>

      {/* Scroll-reveal dashboard screenshot */}
      <div className="w-full mt-8">
        <Image
          src="/images/designer.png"
          alt="Cortex dashboard"
          width={1200}
          height={800}
          className="w-full h-auto transition-all duration-100 ease-out"
          style={{
            opacity,
            clipPath: isDesktop ? `inset(${100 - maskReveal}% 0 0 0)` : "none",
          }}
          priority
        />
      </div>
    </section>
  )
}
