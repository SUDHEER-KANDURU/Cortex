"use client"

// =============================================================================
// MagneticCursor — premium engineering cursor
//
// Two elements appended directly to <body> (bypasses backdrop-filter z stacking):
//   dot  — 5px solid circle, tight lerp (0.35), tracks cursor precisely
//   ring — 28px outline circle, looser lerp (0.14), trails slightly behind
//
// Behaviour:
//   - On interactive elements: dot shrinks to 3px, ring expands to 40px
//     with a reduced border opacity. No color change — only geometry.
//   - On text/copy: ring shrinks to 16px (text I-beam feel)
//   - All transitions are CSS (GPU-accelerated), not JS
//
// The cursor makes the page feel alive and precise without adding visual noise.
// =============================================================================

import { useEffect } from "react"

export function MagneticCursor() {
  useEffect(() => {
    if (!window.matchMedia("(pointer: fine)").matches) return

    // ── Elements ──────────────────────────────────────────────────────────────
    const dot  = document.createElement("div")
    const ring = document.createElement("div")

    // Fixed position anchors — transform moves them each frame
    const fixedBase = [
      "position:fixed",
      "top:0", "left:0",
      "pointer-events:none",
      "will-change:transform",
      "z-index:2147483647",
      "opacity:0",
      "transition:opacity 0.15s ease",
    ].join(";")

    dot.style.cssText  = fixedBase
    ring.style.cssText = fixedBase

    // ── Dot inner — 5px filled circle ────────────────────────────────────────
    const dotInner = document.createElement("div")
    Object.assign(dotInner.style, {
      position:     "relative",
      transform:    "translate(-50%,-50%)",
      borderRadius: "50%",
      background:   "#0a0a0a",
      width:  "5px",
      height: "5px",
      // Size transitions — CSS handles it, no JS needed
      transition: "width 0.2s cubic-bezier(0.16,1,0.3,1), height 0.2s cubic-bezier(0.16,1,0.3,1)",
    })
    dot.appendChild(dotInner)

    // ── Ring inner — 28px outline circle ─────────────────────────────────────
    const ringInner = document.createElement("div")
    Object.assign(ringInner.style, {
      position:     "relative",
      transform:    "translate(-50%,-50%)",
      borderRadius: "50%",
      border:       "1px solid rgba(10,10,10,0.22)",
      width:  "28px",
      height: "28px",
      transition: [
        "width 0.3s cubic-bezier(0.16,1,0.3,1)",
        "height 0.3s cubic-bezier(0.16,1,0.3,1)",
        "border-color 0.25s ease",
        "border-width 0.25s ease",
      ].join(", "),
    })
    ring.appendChild(ringInner)

    // Append last — guaranteed above all stacking contexts
    document.body.appendChild(ring)
    document.body.appendChild(dot)

    // ── Hide native cursor ────────────────────────────────────────────────────
    const styleEl = document.createElement("style")
    styleEl.textContent = "@media (pointer: fine) { * { cursor: none !important; } }"
    document.head.appendChild(styleEl)

    // ── Lerp state ────────────────────────────────────────────────────────────
    let rafId: number
    // Dot position — tight
    let dX = -300, dY = -300
    // Ring position — trailing
    let rX = -300, rY = -300
    // Target
    let tX = -300, tY = -300
    let hasMovedOnce = false

    // ── Interactive / text selectors ──────────────────────────────────────────
    const INTERACTIVE = [
      "a[href]", "button", "[role='button']",
      "input[type='submit']", "[data-magnetic]", "label",
    ].join(",")

    const TEXT = "p, span, li, blockquote, h1, h2, h3, h4, td"

    // ── State tracking ────────────────────────────────────────────────────────
    type CursorMode = "default" | "hover" | "text"
    let mode: CursorMode = "default"

    function applyMode(next: CursorMode) {
      if (next === mode) return
      mode = next
      switch (next) {
        case "hover":
          // Dot smaller, ring larger — geometry only
          dotInner.style.width  = "3px"
          dotInner.style.height = "3px"
          ringInner.style.width  = "40px"
          ringInner.style.height = "40px"
          ringInner.style.borderColor = "rgba(10,10,10,0.14)"
          break
        case "text":
          // Ring contracts to a narrow bar (I-beam feel)
          dotInner.style.width  = "2px"
          dotInner.style.height = "16px"
          dotInner.style.borderRadius = "1px"
          ringInner.style.width  = "16px"
          ringInner.style.height = "16px"
          ringInner.style.borderColor = "rgba(10,10,10,0.10)"
          break
        default:
          dotInner.style.width  = "5px"
          dotInner.style.height = "5px"
          dotInner.style.borderRadius = "50%"
          ringInner.style.width  = "28px"
          ringInner.style.height = "28px"
          ringInner.style.borderColor = "rgba(10,10,10,0.22)"
          ringInner.style.borderWidth = "1px"
          break
      }
    }

    // ── Mouse tracking ────────────────────────────────────────────────────────
    const onMove = (e: MouseEvent) => {
      tX = e.clientX
      tY = e.clientY

      if (!hasMovedOnce) {
        hasMovedOnce = true
        dX = tX; dY = tY
        rX = tX; rY = tY
        dot.style.opacity  = "1"
        ring.style.opacity = "1"
      }

      // Mode detection — check what the cursor is currently over
      const target = e.target as HTMLElement
      if (target.closest(INTERACTIVE)) {
        applyMode("hover")
      } else if (target.closest(TEXT)) {
        applyMode("text")
      } else {
        applyMode("default")
      }
    }

    // ── RAF render loop ───────────────────────────────────────────────────────
    const tick = () => {
      // Dot — tight (0.35), stays close to cursor
      dX += (tX - dX) * 0.35
      dY += (tY - dY) * 0.35

      // Ring — looser (0.14), trails naturally
      rX += (tX - rX) * 0.14
      rY += (tY - rY) * 0.14

      dot.style.transform  = `translate(${dX}px,${dY}px) translateZ(0)`
      ring.style.transform = `translate(${rX}px,${rY}px) translateZ(0)`

      rafId = requestAnimationFrame(tick)
    }

    const onLeave  = () => { dot.style.opacity = "0"; ring.style.opacity = "0" }
    const onEnter  = () => {
      if (hasMovedOnce) { dot.style.opacity = "1"; ring.style.opacity = "1" }
    }

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

  return null
}
