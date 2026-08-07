"use client"

import { useEffect, useRef } from "react"

/**
 * ScrollProgress — thin brand-colored bar at the very top of the viewport.
 * Uses direct DOM mutation (no React state) for 60fps performance.
 * The bar scaleX tracks document scroll progress 0→1.
 */
export function ScrollProgress() {
  const barRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const bar = barRef.current
    if (!bar) return

    let rafId: number
    let lastProgress = -1

    const update = () => {
      const scrollTop  = window.scrollY
      const docHeight  = document.documentElement.scrollHeight - window.innerHeight
      const progress   = docHeight > 0 ? Math.min(scrollTop / docHeight, 1) : 0

      // Only paint if value has actually changed — avoids redundant style writes
      if (Math.abs(progress - lastProgress) > 0.0005) {
        lastProgress = progress
        bar.style.transform = `scaleX(${progress})`
      }
    }

    const onScroll = () => {
      cancelAnimationFrame(rafId)
      rafId = requestAnimationFrame(update)
    }

    window.addEventListener("scroll", onScroll, { passive: true })
    update()

    return () => {
      window.removeEventListener("scroll", onScroll)
      cancelAnimationFrame(rafId)
    }
  }, [])

  return (
    <div
      aria-hidden="true"
      style={{
        position: "fixed",
        top: 0, left: 0,
        width: "100%",
        height: "2px",
        zIndex: 9999,
        pointerEvents: "none",
      }}
    >
      {/* Track */}
      <div style={{
        position: "absolute", inset: 0,
        background: "rgba(255,255,255,0.04)",
      }} />
      {/* Fill — brand gradient + subtle glow */}
      <div
        ref={barRef}
        className="scroll-progress-bar"
        style={{
          position: "absolute", inset: 0,
          background: "linear-gradient(90deg, var(--primary) 0%, #38bdf8 55%, var(--primary) 100%)",
          backgroundSize: "200% 100%",
          transformOrigin: "left center",
          transform: "scaleX(0)",
          /* CSS animation for the gradient shimmer sweep */
          animation: "gradient-shift 4s ease infinite",
          boxShadow: "0 0 10px var(--primary-glow), 0 0 4px rgba(0,229,168,0.3)",
        }}
      />
    </div>
  )
}
