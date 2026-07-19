"use client"

import type React from "react"
import { useEffect, useRef, useState, useCallback } from "react"

// =============================================================================
// SectionTitle — premium heading component with deliberate scramble + reveal.
//
// When the heading enters the viewport it:
//   1. Slides up from y+32 with a blur-in (0.9s cubic-ease)
//   2. Optionally runs a text scramble that settles character-by-character
//      (disabled if prefers-reduced-motion)
//
// The scramble effect is now more deliberate: characters reveal left-to-right
// with a tighter 150ms spread so it feels intentional, not chaotic.
// =============================================================================

interface SectionTitleProps {
  children: React.ReactNode
  className?: string
  scramble?: boolean
  as?: "h1" | "h2" | "h3"
}

const CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

function useTextScramble(text: string, trigger: boolean, duration = 480) {
  const [display, setDisplay] = useState(text)
  const frame = useRef<number | null>(null)
  const startTs = useRef<number | null>(null)

  const run = useCallback(
    (ts: number) => {
      if (!startTs.current) startTs.current = ts
      const elapsed = ts - startTs.current

      setDisplay(
        text
          .split("")
          .map((ch, i) => {
            if (ch === " ") return " "
            // Tight left-to-right reveal: each char reveals proportionally
            // to elapsed time, spread over the first 150ms of the animation
            const revealAt = (i / Math.max(text.length - 1, 1)) * 150
            if (elapsed > revealAt) return ch
            return CHARS[Math.floor(Math.random() * CHARS.length)]
          })
          .join(""),
      )

      if (elapsed < duration) {
        frame.current = requestAnimationFrame(run)
      } else {
        setDisplay(text)
      }
    },
    [text, duration],
  )

  useEffect(() => {
    if (!trigger) return
    startTs.current = null
    frame.current = requestAnimationFrame(run)
    return () => {
      if (frame.current) cancelAnimationFrame(frame.current)
    }
  }, [trigger, run])

  return display
}

export function SectionTitle({
  children,
  className = "",
  scramble = true,
  as: Tag = "h2",
}: SectionTitleProps) {
  const [visible, setVisible] = useState(false)
  const ref = useRef<HTMLHeadingElement>(null)

  const prefersReducedMotion =
    typeof window !== "undefined"
      ? window.matchMedia("(prefers-reduced-motion: reduce)").matches
      : false

  useEffect(() => {
    const el = ref.current
    if (!el) return

    // Use a slightly earlier trigger so the heading feels like it "arrives"
    // with purpose rather than appearing right at the 50% threshold.
    const obs = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !visible) setVisible(true)
      },
      { threshold: 0.15, rootMargin: "0px 0px -20px 0px" },
    )
    obs.observe(el)
    return () => obs.disconnect()
  }, [visible])

  const plainText = typeof children === "string" ? children : ""
  const shouldScramble = scramble && !!plainText && !prefersReducedMotion
  const scrambled = useTextScramble(plainText, visible && shouldScramble, 480)

  return (
    <Tag
      ref={ref as React.RefObject<HTMLHeadingElement>}
      className={className}
      style={{
        fontFamily: "var(--font-display,'Syne',system-ui,sans-serif)",
        color: "oklch(0.03 0 0)",
        letterSpacing: "-0.045em",
        lineHeight: 1.06,
        willChange: "opacity, transform, filter",
        overflow: "visible",
        // Arriving state — blur-up from below
        opacity: visible ? 1 : 0,
        transform: visible ? "translateY(0)" : "translateY(32px)",
        filter: visible ? "blur(0px)" : "blur(10px)",
        transition: [
          "opacity 0.9s cubic-bezier(0.22, 1, 0.36, 1)",
          "transform 0.9s cubic-bezier(0.22, 1, 0.36, 1)",
          "filter 0.7s cubic-bezier(0.22, 1, 0.36, 1)",
        ].join(", "),
      }}
    >
      {shouldScramble && visible ? scrambled : children}
    </Tag>
  )
}
