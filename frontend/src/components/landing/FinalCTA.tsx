"use client"

/**
 * FinalCTA — Section reveal + Framer Motion button interactions.
 *
 * Motion:
 *  - Entire section wrapped in SectionReveal (whileInView fade-up)
 *  - Eyebrow pill fades in with delay
 *  - Headline uses staggered line reveal
 *  - Pipeline badges stagger in with scale spring
 *  - Primary CTA: spring lift on hover, compress on tap
 */

import { motion, useReducedMotion } from "framer-motion"
import { ArrowUpRight } from "lucide-react"
import { DashboardLink } from "@/components/shared/DashboardLink"
import { SectionReveal } from "@/components/shared/PageTransition"
import { SPRING, DURATION, EASE, staggerFastContainer, staggerFastChild } from "@/lib/utils/motion"

// ── Motion presets ─────────────────────────────────────────────────────────

const PRIMARY_HOVER = {
  y:          -3,
  boxShadow:  "0 16px 48px var(--primary-glow), inset 0 1px 0 rgba(255,255,255,0.22)",
  filter:     "brightness(1.1)",
  transition: SPRING.snappy,
}
const PRIMARY_TAP = {
  scale:      0.96,
  y:          1,
  transition: { duration: DURATION.micro },
}

const HEADLINE_LINE = (i: number) => ({
  hidden:  { opacity: 0, y: 20, filter: "blur(6px)" },
  visible: {
    opacity: 1, y: 0, filter: "blur(0px)",
    transition: { duration: DURATION.reveal, delay: 0.1 + i * 0.1, ease: EASE.out },
  },
})

export function PortfolioFinalCTA() {
  const prefersReduced = useReducedMotion()

  return (
    <section
      id="contact"
      className="py-24 md:py-36 relative overflow-hidden"
      style={{
        borderTop:          "1px solid var(--cx-card-border)",
        background:         "var(--cx-section-bg)",
      }}
    >
      {/* Ambient orbs — CSS only, no JS */}
      <div style={{ position: "absolute", top: "-10%", left: "5%", width: "400px", height: "400px", borderRadius: "50%", background: "radial-gradient(circle, rgba(0,0,0,0.025) 0%, transparent 70%)", filter: "blur(60px)", animation: "orb-drift 18s ease-in-out infinite", pointerEvents: "none" }} />
      <div style={{ position: "absolute", bottom: "-5%", right: "8%", width: "300px", height: "300px", borderRadius: "50%", background: "radial-gradient(circle, rgba(0,0,0,0.02) 0%, transparent 70%)", filter: "blur(48px)", animation: "orb-drift 22s ease-in-out infinite reverse", pointerEvents: "none" }} />

      <div className="max-w-[1280px] mx-auto px-6 md:px-12 relative z-10">
        <div className="max-w-3xl mx-auto text-center">

          {/* Eyebrow */}
          <SectionReveal delay={0} direction="none">
            <div
              className="cx-pill inline-flex items-center gap-2 mb-6 px-4 py-2 rounded-full"
              style={{ backdropFilter: "blur(8px) saturate(180%)", WebkitBackdropFilter: "blur(8px) saturate(180%)" }}
            >
              <span style={{ width: 6, height: 6, borderRadius: "50%", background: "var(--cx-text)", display: "inline-block", animation: "pulse-dot 2s ease-in-out infinite" }} />
              <span className="cx-text-mono" style={{ fontSize: "11px", fontWeight: 600, letterSpacing: "0.1em", textTransform: "uppercase", fontFamily: "var(--font-mono,'JetBrains Mono',monospace)" }}>
                Free &amp; Open Source
              </span>
            </div>
          </SectionReveal>

          {/* Headline — line by line */}
          <h2
            className="cx-text text-[42px] md:text-[56px] lg:text-[72px] font-semibold tracking-tight text-balance"
            style={{ fontFamily: "var(--font-sans,'Geist',system-ui,sans-serif)", letterSpacing: "-0.045em", lineHeight: 1.04 }}
          >
            <motion.span
              className="block"
              variants={prefersReduced ? undefined : HEADLINE_LINE(0)}
              initial={prefersReduced ? false : "hidden"}
              whileInView="visible"
              viewport={{ once: true, amount: 0.5 }}
            >
              Have a codebase?
            </motion.span>
            <motion.span
              className="block"
              style={{ opacity: 0.45 }}
              variants={prefersReduced ? undefined : HEADLINE_LINE(1)}
              initial={prefersReduced ? false : "hidden"}
              whileInView="visible"
              viewport={{ once: true, amount: 0.5 }}
            >
              Let Cortex map it.
            </motion.span>
          </h2>

          <SectionReveal delay={0.25} direction="up">
            <p className="cx-text-muted mt-6 text-base leading-[1.7] max-w-[480px] mx-auto">
              Paste a GitHub URL and get architecture diagrams, learning paths, and interview prep in seconds. AI-powered analysis with full-text search and interactive graph exploration.
            </p>
          </SectionReveal>

          {/* Pipeline badges — staggered scale-in */}
          <motion.div
            className="flex flex-wrap items-center justify-center gap-2 mt-10"
            variants={prefersReduced ? undefined : staggerFastContainer}
            initial={prefersReduced ? false : "hidden"}
            whileInView="visible"
            viewport={{ once: true, amount: 0.4 }}
          >
            {["Scan Repo", "Parse AST", "Build Graph", "Generate Artifacts"].map((step, i) => (
              <motion.div
                key={step}
                className="flex items-center gap-2"
                variants={prefersReduced ? undefined : staggerFastChild}
              >
                <motion.span
                  className="cx-pill cx-text-mono"
                  style={{ padding: "6px 16px", borderRadius: "100px", fontSize: "11px", fontWeight: 600, backdropFilter: "blur(8px) saturate(180%)", WebkitBackdropFilter: "blur(8px) saturate(180%)", letterSpacing: "0.04em", fontFamily: "var(--font-mono,'JetBrains Mono',monospace)" }}
                  whileHover={prefersReduced ? {} : { y: -2, transition: SPRING.snappy }}
                >
                  {step}
                </motion.span>
                {i < 3 && <span className="cx-text-faint" style={{ fontSize: "14px", fontWeight: 300 }}>→</span>}
              </motion.div>
            ))}
          </motion.div>

          {/* CTAs */}
          <SectionReveal delay={0.35} direction="up">
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mt-10">

              {/* Primary CTA */}
              <motion.div
                whileHover={prefersReduced ? {} : PRIMARY_HOVER}
                whileTap={prefersReduced ? {} : PRIMARY_TAP}
              >
                <DashboardLink
                  className="group inline-flex items-center justify-center gap-2 px-9 py-4 text-base font-semibold rounded-full"
                  style={{
                    background:  "var(--primary)",
                    color:       "#FFFFFF",
                    boxShadow:   "var(--shadow-md)",
                  }}
                >
                  Analyze a Repository
                  <ArrowUpRight className="w-4 h-4 transition-transform duration-300 group-hover:translate-x-0.5 group-hover:-translate-y-0.5" />
                </DashboardLink>
              </motion.div>

              {/* CTAs */}
            </div>
          </SectionReveal>

          <SectionReveal delay={0.45} direction="none">
            <p className="cx-text-faint mt-8 text-xs" style={{ fontFamily: "var(--font-mono,'JetBrains Mono',monospace)", letterSpacing: "0.06em" }}>
              MIT License · Built at SRMIST Chennai · Zero cloud dependencies
            </p>
          </SectionReveal>

        </div>
      </div>
    </section>
  )
}
