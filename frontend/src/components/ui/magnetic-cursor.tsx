"use client"

// ─────────────────────────────────────────────────────────────────────────────
// MagneticCursor — portal-based, always on top
//
// Root cause of cursor going behind navbar:
//   backdrop-filter on the header creates an isolated composited layer.
//   Any sibling element — even z-index:99999 — can be drawn behind it
//   because the compositor paints backdrop-filter layers last within their
//   stacking context.
//
// Solution: append cursor elements directly to <body> via a portal,
//   making them the absolute last nodes in the DOM paint order.
//   Also use pointer-events:none so they never interfere with interaction.
// ─────────────────────────────────────────────────────────────────────────────

import { useEffect } from "react"

export function MagneticCursor() {
  useEffect(() => {
    // Only run on fine-pointer (mouse) devices
    if (!window.matchMedia("(pointer: fine)").matches) return

    // ── Create cursor elements directly on body ──────────────────────────────
    // Being the last children of body means they are ALWAYS painted on top,
    // above any backdrop-filter stacking context in the page.
    const dot  = document.createElement("div")
    const ring = document.createElement("div")

    const dotInner  = document.createElement("div")
    const ringInner = document.createElement("div")

    // Outer wrappers — position anchors
    const baseStyle = [
      "position:fixed", "top:0", "left:0",
      "pointer-events:none",
      "will-change:transform",
      "z-index:2147483647",    // INT_MAX — absolute maximum z-index
      "opacity:0",
      "transition:opacity 0.12s ease",
    ].join(";")

    dot.style.cssText  = baseStyle
    ring.style.cssText = baseStyle

    // Dot inner
    dotInner.className = "cursor-dot-inner"
    Object.assign(dotInner.style, {
      position: "relative",
      transform: "translate(-50%,-50%)",
      borderRadius: "50%",
      background: "#0a0a0a",
      width: "7px",
      height: "7px",
    })

    // Ring inner
    ringInner.className = "cursor-ring-inner"
    Object.assign(ringInner.style, {
      position: "relative",
      transform: "translate(-50%,-50%)",
      borderRadius: "50%",
      border: "1.5px solid rgba(10,10,10,0.28)",
      width: "34px",
      height: "34px",
    })

    dot.appendChild(dotInner)
    ring.appendChild(ringInner)

    // Append as LAST children of body — paint order guarantees top-most
    document.body.appendChild(ring)
    document.body.appendChild(dot)

    // ── cursor: none injection ───────────────────────────────────────────────
    const styleEl      = document.createElement("style")
    styleEl.textContent = "@media (pointer: fine) { * { cursor: none !important; } }"
    document.head.appendChild(styleEl)

    // ── State ────────────────────────────────────────────────────────────────
    let rafId: number
    let tX = -300, tY = -300
    let cX = -300, cY = -300
    let hasMovedOnce = false

    const INTERACTIVE = [
      "a[href]", "button", "[role='button']",
      "input[type='submit']", "label[for]",
    ].join(",")

    // ── Mouse tracking ───────────────────────────────────────────────────────
    const onMove = (e: MouseEvent) => {
      tX = e.clientX
      tY = e.clientY

      if (!hasMovedOnce) {
        hasMovedOnce = true
        cX = tX; cY = tY          // snap on first move — no drift from corner
        dot.style.opacity  = "1"
        ring.style.opacity = "1"
      }

      // Hover detection
      const el = (e.target as HTMLElement).closest(INTERACTIVE) as HTMLElement | null
      if (el) {
        dot.classList.add("cursor-hover")
        ring.classList.add("cursor-hover")
        // Gentle magnetic pull
        const r    = el.getBoundingClientRect()
        const ecx  = r.left + r.width  / 2
        const ecy  = r.top  + r.height / 2
        const dx   = tX - ecx, dy = tY - ecy
        const dist = Math.sqrt(dx * dx + dy * dy)
        if (dist < 70) { tX -= dx * 0.20; tY -= dy * 0.20 }
      } else {
        dot.classList.remove("cursor-hover")
        ring.classList.remove("cursor-hover")
      }
    }

    // ── RAF loop ─────────────────────────────────────────────────────────────
    const tick = () => {
      cX += (tX - cX) * 0.30          // dot — tight
      cY += (tY - cY) * 0.30
      const rX = cX + (tX - cX) * 0.10  // ring — trailing
      const rY = cY + (tY - cY) * 0.10

      dot.style.transform  = `translate(${cX}px,${cY}px) translateZ(0)`
      ring.style.transform = `translate(${rX}px,${rY}px) translateZ(0)`
      rafId = requestAnimationFrame(tick)
    }

    const onLeave = () => { dot.style.opacity = "0"; ring.style.opacity = "0" }
    const onEnter = () => { if (hasMovedOnce) { dot.style.opacity = "1"; ring.style.opacity = "1" } }

    window.addEventListener("mousemove",    onMove,   { passive: true })
    document.addEventListener("mouseleave", onLeave)
    document.addEventListener("mouseenter", onEnter)
    rafId = requestAnimationFrame(tick)

    // ── Cleanup ───────────────────────────────────────────────────────────────
    return () => {
      window.removeEventListener("mousemove",    onMove)
      document.removeEventListener("mouseleave", onLeave)
      document.removeEventListener("mouseenter", onEnter)
      cancelAnimationFrame(rafId)
      styleEl.remove()
      dot.remove()
      ring.remove()
    }
  }, [])

  // Render nothing — elements are created imperatively in the DOM
  return null
}
