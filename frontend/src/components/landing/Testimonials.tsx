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
  },
  {
    id: 2,
    quote: "The learning path it built from our Spring Boot codebase was exactly what I needed as a new joiner. I understood the system in days instead of weeks.",
    author: "Priya Nair",
    role: "Backend Developer",
    avatar: "/images/imgi_106_user86.webp",
  },
  {
    id: 3,
    quote: "We caught a circular dependency that had been silently degrading our build times for months. Cortex surfaced it in the first run.",
    author: "Marcus Lin",
    role: "Platform Lead",
    avatar: "/images/imgi_105_user85.webp",
  },
  {
    id: 4,
    quote: "Zero API keys, runs on my laptop, generates real insight. This is how developer tooling should work.",
    author: "Fatima Al-Hassan",
    role: "Full Stack Engineer",
    avatar: "/images/imgi_102_user82.webp",
  },
  {
    id: 5,
    quote: "The interview prep questions it generated from my own project were harder and more relevant than anything I found online. I got the offer.",
    author: "Rohan Sharma",
    role: "CS Graduate",
    avatar: "/images/imgi_100_user80.webp",
  },
  {
    id: 6,
    quote: "Our tech lead used Cortex to audit a vendor codebase before acquisition. Found three critical design flaws in an hour.",
    author: "Elena Kowalski",
    role: "Engineering Manager",
    avatar: "/images/imgi_107_user87.webp",
  },
  {
    id: 7,
    quote: "We integrated Cortex into our onboarding process. New engineers are productive 40% faster now because they actually understand the system architecture.",
    author: "David Okonkwo",
    role: "CTO at B2B SaaS",
    avatar: "/images/imgi_108_user88.webp",
  },
]

type Testimonial = typeof testimonials[0]

function Card({ t }: { t: Testimonial }) {
  return (
    <article
      data-spotlight
      className="relative flex-shrink-0 w-[85vw] md:w-[400px] p-6 md:p-8 rounded-3xl overflow-hidden"
      style={{
        background: "rgba(255,255,255,0.65)",
        backdropFilter: "blur(8px) saturate(200%) brightness(1.02)",
        WebkitBackdropFilter: "blur(8px) saturate(200%) brightness(1.02)",
        border: "1px solid rgba(255,255,255,0.88)",
        boxShadow: "0 4px 24px rgba(0,0,0,0.06), inset 0 1px 0 rgba(255,255,255,1)",
      }}>
      <div className="flex items-center gap-3 mb-4">
        <Image
          src={t.avatar || "/placeholder.svg"}
          alt={t.author}
          width={44}
          height={44}
          className="rounded-full"
          style={{ border: "1px solid rgba(0,0,0,0.08)" }}
        />
        <div>
          <div className="font-semibold text-sm" style={{ color: "#111" }}>{t.author}</div>
          <div className="text-xs" style={{ color: "rgba(0,0,0,0.45)" }}>{t.role}</div>
        </div>
      </div>
      <blockquote
        className="text-sm leading-relaxed"
        style={{ color: "rgba(0,0,0,0.7)", fontWeight: 500 }}>
        &ldquo;{t.quote}&rdquo;
      </blockquote>
      {/* Subtle corner accent — ink, no colour */}
      <div style={{
        position: "absolute", bottom: -16, right: -16,
        width: 80, height: 80, borderRadius: "50%",
        background: "rgba(0,0,0,0.03)",
        pointerEvents: "none",
      }} />
    </article>
  )
}

export function PortfolioTestimonials() {
  const [isPaused, setIsPaused] = useState(false)
  const dup  = [...testimonials, ...testimonials]
  const dupR = [...testimonials.slice().reverse(), ...testimonials.slice().reverse()]
  const mobile = testimonials.slice(0, 6)

  return (
    <section id="testimonials" className="py-20 overflow-hidden md:py-32 pb-0 relative"
      style={{
        borderTop: "1px solid rgba(255,255,255,0.65)",
        background: "rgba(255,255,255,0.52)",
        backdropFilter: "blur(8px) saturate(160%)",
        WebkitBackdropFilter: "blur(8px) saturate(160%)",
        boxShadow: "inset 0 1px 0 rgba(255,255,255,0.9)",
      }}>

      {/* Bottom fade — masks the scroll rows */}
      <div className="absolute bottom-0 left-0 right-0 h-64 pointer-events-none z-20 hidden lg:block"
        style={{ background: "linear-gradient(to top,#ffffff,rgba(255,255,255,0.9),transparent)" }} />

      {/* ── Desktop: two scrolling rows ── */}
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
          <div key={row} className={row === 0 ? "mb-5" : ""}>
            <div
              className={`flex gap-5 ${cls}`}
              onMouseEnter={() => setIsPaused(true)}
              onMouseLeave={() => setIsPaused(false)}
              style={{ animationPlayState: isPaused ? "paused" : "running" }}>
              {items.map((t, i) => <Card key={`${row}-${t.id}-${i}`} t={t} />)}
            </div>
          </div>
        ))}
      </div>

      {/* ── Mobile: sticky stack ── */}
      <div className="lg:hidden max-w-[1280px] mx-auto px-6 md:px-12">
        <div className="mb-12 md:mb-16">
          <SectionTitle className="text-3xl md:text-4xl lg:text-5xl font-semibold tracking-tight">
            What developers say
          </SectionTitle>
        </div>
        <div className="relative">
          {mobile.map((t, index) => (
            <div key={t.id} className="sticky pt-8" style={{ top: `${70 + index * 8}px`, zIndex: index + 1 }}>
              <Card t={t} />
            </div>
          ))}
        </div>
      </div>

      <div className="absolute bottom-0 left-0 right-0 h-48 pointer-events-none z-10 lg:hidden"
        style={{ background: "linear-gradient(to top,#ffffff,rgba(255,255,255,0.9),transparent)" }} />
    </section>
  )
}
