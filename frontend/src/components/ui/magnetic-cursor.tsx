"use client"

// ─────────────────────────────────────────────────────────────────────────────
// MagneticCursor
//
// Fixes over original:
// 1. No React state for position — DOM transform is mutated directly in rAF
//    (eliminates 60fps setState → re-render cascade, removes jank)
// 2. CSS cursor:none injected via a <style> tag rendered to the document head
//    (styled-jsx is Pages Router only; doesn't work in App Router)
// 3. Hover scale driven by adding/removing a CSS class instead of inline style
//    writes, which lets the CSS transition run cleanly
// ─────────────────────────────────────────────────────────────────────────────

import { useEffect, useRef } from "react"

export function MagneticCursor() {
  const dotRef   = useRef<HTMLDivElement>(null)
  const ringRef  = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const dot  = dotRef.current
    const ring = ringRef.current
    if (!dot || !ring) return

    // Inject cursor:none via a real <style> element so App Router picks it up
    const styleEl = document.createElement("style")
    styleEl.textContent = "@media (min-width: 768px) { * { cursor: none !important; } }"
    document.head.appendChild(styleEl)

    let rafId: number
    let targetX = 0, targetY = 0
    let currentX = 0, currentY = 0

    const INTERACTIVE = [
      "a[href]",
      "button",
      '[data-slot="button"]',
      'input[type="submit"]',
      '[role="button"]',
    ].join(",")

    const onMouseMove = (e: MouseEvent) => {
      targetX = e.clientX
      targetY = e.clientY

      const el = (e.target as HTMLElement).closest(INTERACTIVE) as HTMLElement | null
      if (el) {
        dot.classList.add("cursor-hover")
        ring.classList.add("cursor-hover")

        // Magnetic pull within 80px radius
        const rect = el.getBoundingClientRect()
        const cx = rect.left + rect.width  / 2
        const cy = rect.top  + rect.height / 2
        const dx = targetX - cx
        const dy = targetY - cy
        const dist = Math.sqrt(dx * dx + dy * dy)
        if (dist < 80) {
          targetX -= dx * 0.3
          targetY -= dy * 0.3
        }
      } else {
        dot.classList.remove("cursor-hover")
        ring.classList.remove("cursor-hover")
      }
    }

    const tick = () => {
      // Smooth interpolation — no setState, pure DOM mutation
      currentX += (targetX - currentX) * 0.15
      currentY += (targetY - currentY) * 0.15

      dot.style.transform  = `translate(${currentX}px, ${currentY}px)`
      ring.style.transform = `translate(${currentX}px, ${currentY}px)`

      rafId = requestAnimationFrame(tick)
    }

    window.addEventListener("mousemove", onMouseMove, { passive: true })
    rafId = requestAnimationFrame(tick)

    return () => {
      window.removeEventListener("mousemove", onMouseMove)
      cancelAnimationFrame(rafId)
      styleEl.remove()
    }
  }, [])

  return (
    <>
      {/* Dot */}
      <div
        ref={dotRef}
        className="cursor-dot"
        style={{
          position: "fixed",
          top: 0,
          left: 0,
          pointerEvents: "none",
          zIndex: 9999,
          mixBlendMode: "difference",
        }}
      >
        <div
          style={{
            position: "relative",
            transform: "translate(-50%, -50%)",
            borderRadius: "50%",
            background: "#fff",
            width: "8px",
            height: "8px",
            transition: "width 0.2s, height 0.2s",
          }}
          className="cursor-dot-inner"
        />
      </div>

      {/* Ring */}
      <div
        ref={ringRef}
        className="cursor-ring"
        style={{
          position: "fixed",
          top: 0,
          left: 0,
          pointerEvents: "none",
          zIndex: 9998,
          mixBlendMode: "difference",
        }}
      >
        <div
          style={{
            position: "relative",
            transform: "translate(-50%, -50%)",
            borderRadius: "50%",
            border: "1px solid rgba(255,255,255,0.4)",
            width: "32px",
            height: "32px",
            transition: "width 0.3s, height 0.3s",
          }}
          className="cursor-ring-inner"
        />
      </div>

      {/* Hover-size styles — scoped to cursor elements only */}
      <style>{`
        @media (min-width: 768px) {
          .cursor-dot,
          .cursor-ring { display: block; }
        }
        @media (max-width: 767px) {
          .cursor-dot,
          .cursor-ring { display: none; }
        }
        .cursor-dot.cursor-hover   .cursor-dot-inner  { width: 40px !important; height: 40px !important; }
        .cursor-ring.cursor-hover  .cursor-ring-inner { width: 60px !important; height: 60px !important; }
      `}</style>
    </>
  )
}
