"use client"

import { useState } from "react"
import Image from "next/image"
import { SectionTitle } from "@/components/ui/section-title"

const testimonials = [
  {
    id: 1,
    quote: "Cortex mapped our entire monolith in under 5 minutes. The architecture diagram it generated was more accurate than the one our team hand-drew six months ago.",
    author: "Arjun Mehta",
    role: "Senior Engineer at FinTech Startup",
    avatar: "/images/imgi_97_user77.webp",
    blurColor: "bg-blue-500",
  },
  {
    id: 2,
    quote: "The learning path it built from our Spring Boot codebase was exactly what I needed as a new joiner. I understood the system in days instead of weeks.",
    author: "Priya Nair",
    role: "Backend Developer",
    avatar: "/images/imgi_106_user86.webp",
    blurColor: "bg-purple-500",
  },
  {
    id: 3,
    quote: "We caught a circular dependency that had been silently degrading our build times for months. Cortex surfaced it in the first run.",
    author: "Marcus Lin",
    role: "Platform Lead",
    avatar: "/images/imgi_105_user85.webp",
    blurColor: "bg-pink-500",
  },
  {
    id: 4,
    quote: "Zero API keys, runs on my laptop, generates real insight. This is how developer tooling should work.",
    author: "Fatima Al-Hassan",
    role: "Full Stack Engineer",
    avatar: "/images/imgi_102_user82.webp",
    blurColor: "bg-emerald-500",
  },
  {
    id: 5,
    quote: "The interview prep questions it generated from my own project were harder and more relevant than anything I found online. I got the offer.",
    author: "Rohan Sharma",
    role: "CS Graduate",
    avatar: "/images/imgi_100_user80.webp",
    blurColor: "bg-orange-500",
  },
  {
    id: 6,
    quote: "Our tech lead used Cortex to audit a vendor codebase before acquisition. Found three critical design flaws in an hour.",
    author: "Elena Kowalski",
    role: "Engineering Manager",
    avatar: "/images/imgi_107_user87.webp",
    blurColor: "bg-cyan-500",
  },
  {
    id: 7,
    quote: "We integrated Cortex into our onboarding process. New engineers are productive 40% faster now because they actually understand the system architecture.",
    author: "David Okonkwo",
    role: "CTO at B2B SaaS",
    avatar: "/images/imgi_108_user88.webp",
    blurColor: "bg-rose-500",
  },
]

export function PortfolioTestimonials() {
  const [isPaused, setIsPaused] = useState(false)
  const dup  = [...testimonials, ...testimonials]
  const dupR = [...testimonials.slice().reverse(), ...testimonials.slice().reverse()]
  const mobile = testimonials.slice(0, 6)

  const Card = ({ t }: { t: typeof testimonials[0] }) => (
    <article className="relative flex-shrink-0 w-[85vw] md:w-[400px] p-6 md:p-8 border bg-card hover:shadow-lg transition-shadow overflow-hidden border-zinc-100 md:px-6 md:py-6 rounded-3xl">
      <div className="flex items-center gap-3 mb-4">
        <Image src={t.avatar || "/placeholder.svg"} alt={t.author} width={48} height={48} className="rounded-full" />
        <div>
          <div className="font-semibold">{t.author}</div>
          <div className="text-sm text-muted-foreground">{t.role}</div>
        </div>
      </div>
      <blockquote className="text-base leading-relaxed font-semibold text-zinc-950 relative z-10">
        &ldquo;{t.quote}&rdquo;
      </blockquote>
      <div className={`absolute -bottom-12 -right-12 w-48 h-48 ${t.blurColor} rounded-full opacity-10`} style={{ filter: "blur(72px)" }} />
    </article>
  )

  return (
    <section id="testimonials" className="py-20 border-border overflow-hidden md:py-32 border-t-[0] pb-0 relative">
      <div className="absolute bottom-0 left-0 right-0 h-96 bg-gradient-to-t from-background via-background/80 to-transparent pointer-events-none z-20 hidden lg:block" />

      {/* Desktop */}
      <div className="hidden lg:block pl-6 md:pl-12">
        <div className="mb-12 md:mb-16 max-w-[1280px]">
          <SectionTitle className="text-3xl md:text-4xl lg:text-5xl font-semibold tracking-tight">
            What developers say
          </SectionTitle>
        </div>

        {[
          { items: dup,  cls: "animate-scroll-left"  },
          { items: dupR, cls: "animate-scroll-right" },
        ].map(({ items, cls }, row) => (
          <div key={row} className={`relative ${row === 0 ? "mb-6" : ""}`}>
            <div className={`flex gap-6 ${cls}`}
              onMouseEnter={() => setIsPaused(true)} onMouseLeave={() => setIsPaused(false)}
              onTouchStart={() => setIsPaused(true)} onTouchEnd={() => setIsPaused(false)}
              style={{ animationPlayState: isPaused ? "paused" : "running" }}>
              {items.map((t, i) => <Card key={`${row}-${t.id}-${i}`} t={t} />)}
            </div>
          </div>
        ))}
      </div>

      {/* Mobile */}
      <div className="lg:hidden max-w-[1280px] mx-auto px-6 md:px-12">
        <div className="mb-12 md:mb-16">
          <SectionTitle className="text-3xl md:text-4xl lg:text-5xl font-semibold tracking-tight">
            What developers say
          </SectionTitle>
        </div>
        <div className="relative">
          {mobile.map((t, index) => (
            <div key={t.id} className="sticky pt-10" style={{ top: `${70 + index * 0}px`, zIndex: index + 1 }}>
              <Card t={t} />
            </div>
          ))}
        </div>
      </div>

      <div className="absolute bottom-0 left-0 right-0 h-64 bg-gradient-to-t from-background via-background/90 to-transparent pointer-events-none z-10 lg:hidden" />
    </section>
  )
}
