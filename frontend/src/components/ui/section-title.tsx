"use client"

import type React from "react"
import { useEffect, useRef, useState, useCallback } from "react"

interface SectionTitleProps {
  children: React.ReactNode
  className?: string
  scramble?: boolean
}

const CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"

function useTextScramble(text: string, trigger: boolean, duration = 600) {
  const [display, setDisplay] = useState(text)
  const frame = useRef<number | null>(null)
  const startTs = useRef<number | null>(null)

  const run = useCallback(
    (ts: number) => {
      if (!startTs.current) startTs.current = ts
      const elapsed  = ts - startTs.current
      const progress = Math.min(elapsed / duration, 1)

      setDisplay(
        text
          .split("")
          .map((ch, i) => {
            if (ch === " ") return " "
            // Each character reveals when its personal stagger deadline passes
            // (spread over the first 200ms of the animation)
            const revealAt = (i / text.length) * 200
            if (elapsed > revealAt) return ch
            return CHARS[Math.floor(Math.random() * CHARS.length)]
          })
          .join(""),
      )

      if (progress < 1) frame.current = requestAnimationFrame(run)
      else setDisplay(text)
    },
    [text, duration],
  )

  useEffect(() => {
    if (!trigger) return
    startTs.current = null
    frame.current = requestAnimationFrame(run)
    return () => { if (frame.current) cancelAnimationFrame(frame.current) }
  }, [trigger, run])

  return display
}

export function SectionTitle({
  children,
  className = "",
  scramble = true,
}: SectionTitleProps) {
  const [visible, setVisible] = useState(false)
  const ref = useRef<HTMLHeadingElement>(null)

  // Detect reduced motion preference — SSR-safe
  const prefersReducedMotion = typeof window !== "undefined"
    ? window.matchMedia("(prefers-reduced-motion: reduce)").matches
    : false

  useEffect(() => {
    const el = ref.current
    if (!el) return
    const obs = new IntersectionObserver(
      ([entry]) => { if (entry.isIntersecting && !visible) setVisible(true) },
      { threshold: 0.2, rootMargin: "0px 0px -30px 0px" },
    )
    obs.observe(el)
    return () => obs.disconnect()
  }, [visible])

  const plainText = typeof children === "string" ? children : ""
  // When reduced motion is preferred, trigger is always false → useTextScramble
  // returns plain text immediately without running the animation loop.
  const scrambled = useTextScramble(plainText, visible && scramble && !!plainText && !prefersReducedMotion, 600)

  return (
    <h2
      ref={ref}
      className={`text-4xl ${className}`}
      style={{
        fontFamily: "var(--font-display,'Syne',system-ui,sans-serif)",
        color: "oklch(0.03 0 0)",
        willChange: "opacity, transform, filter",
        overflow: "visible",
        opacity: visible ? 1 : 0,
        transform: visible ? "none" : "translateY(24px)",
        filter: visible ? "none" : "blur(12px)",
        transition: "opacity 0.9s cubic-bezier(0.16,1,0.3,1), transform 0.9s cubic-bezier(0.16,1,0.3,1), filter 0.9s cubic-bezier(0.16,1,0.3,1)",
      }}
    >
      {scramble && plainText && visible ? scrambled : children}
    </h2>
  )
}
