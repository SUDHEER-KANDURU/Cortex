"use client"

import { useEffect, useRef } from "react"

// ── Scroll progress — thin ink line at very top of viewport ──────────────────
export function ScrollProgress() {
  const barRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const bar = barRef.current
    if (!bar) return

    const update = () => {
      const scrollTop  = window.scrollY
      const docHeight  = document.documentElement.scrollHeight - window.innerHeight
      const progress   = docHeight > 0 ? scrollTop / docHeight : 0
      // Direct DOM mutation — no React state, 60fps smooth
      bar.style.transform = `scaleX(${progress})`
    }

    window.addEventListener("scroll", update, { passive: true })
    update()
    return () => window.removeEventListener("scroll", update)
  }, [])

  return (
    <div
      style={{
        position: "fixed",
        top: 0, left: 0,
        width: "100%",
        height: "2px",
        zIndex: 9999,
        pointerEvents: "none",
        transformOrigin: "left center",
      }}
    >
      {/* Track */}
      <div style={{
        position: "absolute", inset: 0,
        background: "rgba(0,0,0,0.06)",
      }} />
      {/* Fill — liquid glass shimmer */}
      <div
        ref={barRef}
        style={{
          position: "absolute", inset: 0,
          background: "linear-gradient(90deg, #0a0a0a 0%, #555 50%, #0a0a0a 100%)",
          transformOrigin: "left center",
          transform: "scaleX(0)",
          transition: "transform 0.1s linear",
        }}
      />
    </div>
  )
}
