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
      const revealed = Math.floor(progress * text.length)

      setDisplay(
        text
          .split("")
          .map((ch, i) => {
            if (ch === " ") return " "
            if (i < revealed) return ch
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
  const scrambled = useTextScramble(plainText, visible && scramble && !!plainText, 600)

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
