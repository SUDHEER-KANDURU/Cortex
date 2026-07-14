"use client"

import { useRef, type ReactNode } from "react"

// ── SpotlightCard — radial light that follows the mouse inside the card ───────
// Usage: wrap any card content with <SpotlightCard>...</SpotlightCard>
interface SpotlightCardProps {
  children: ReactNode
  className?: string
  style?: React.CSSProperties
  spotlightColor?: string
}

export function SpotlightCard({
  children,
  className = "",
  style = {},
  spotlightColor = "rgba(255,255,255,0.08)",
}: SpotlightCardProps) {
  const cardRef  = useRef<HTMLDivElement>(null)
  const glowRef  = useRef<HTMLDivElement>(null)

  const onMouseMove = (e: React.MouseEvent<HTMLDivElement>) => {
    const card = cardRef.current
    const glow = glowRef.current
    if (!card || !glow) return
    const rect = card.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top
    glow.style.background = `radial-gradient(280px circle at ${x}px ${y}px, ${spotlightColor}, transparent 70%)`
    glow.style.opacity = "1"
  }

  const onMouseLeave = () => {
    const glow = glowRef.current
    if (glow) glow.style.opacity = "0"
  }

  return (
    <div
      ref={cardRef}
      className={className}
      style={{ position: "relative", ...style }}
      onMouseMove={onMouseMove}
      onMouseLeave={onMouseLeave}
    >
      {/* Spotlight glow layer */}
      <div
        ref={glowRef}
        style={{
          position: "absolute",
          inset: 0,
          borderRadius: "inherit",
          opacity: 0,
          pointerEvents: "none",
          zIndex: 1,
          transition: "opacity 0.35s ease",
        }}
      />
      {/* Content above glow */}
      <div style={{ position: "relative", zIndex: 2 }}>
        {children}
      </div>
    </div>
  )
}
