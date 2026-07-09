"use client"

import { useEffect, useRef, useState } from "react"

export function MagneticCursor() {
  const cursorRef = useRef<HTMLDivElement>(null)
  const [position, setPosition] = useState({ x: 0, y: 0 })
  const [isHovering, setIsHovering] = useState(false)

  useEffect(() => {
    let rafId: number
    let targetX = 0, targetY = 0
    let currentX = 0, currentY = 0

    const selectors = ["a[href]","button",'[data-slot="button"]','input[type="submit"]','[role="button"]'].join(",")

    const handleMouseMove = (e: MouseEvent) => {
      targetX = e.clientX
      targetY = e.clientY
      const el = (e.target as HTMLElement).closest(selectors)
      if (el) {
        setIsHovering(true)
        const rect = el.getBoundingClientRect()
        const cx = rect.left + rect.width / 2
        const cy = rect.top + rect.height / 2
        const dx = targetX - cx, dy = targetY - cy
        const dist = Math.sqrt(dx*dx + dy*dy)
        if (dist < 80) { targetX -= dx * 0.3; targetY -= dy * 0.3 }
      } else {
        setIsHovering(false)
      }
    }

    const animate = () => {
      currentX += (targetX - currentX) * 0.15
      currentY += (targetY - currentY) * 0.15
      setPosition({ x: currentX, y: currentY })
      rafId = requestAnimationFrame(animate)
    }

    window.addEventListener("mousemove", handleMouseMove)
    animate()
    return () => { window.removeEventListener("mousemove", handleMouseMove); cancelAnimationFrame(rafId) }
  }, [])

  return (
    <>
      <div ref={cursorRef} className="fixed top-0 left-0 pointer-events-none z-[9999] mix-blend-difference hidden md:block"
        style={{ transform: `translate(${position.x}px,${position.y}px)`, transition: isHovering ? "width 0.2s,height 0.2s" : "none" }}>
        <div className="relative -translate-x-1/2 -translate-y-1/2 rounded-full bg-white"
          style={{ width: isHovering ? "40px" : "8px", height: isHovering ? "40px" : "8px", transition: "width 0.2s,height 0.2s" }} />
      </div>
      <div className="fixed top-0 left-0 pointer-events-none z-[9998] mix-blend-difference hidden md:block"
        style={{ transform: `translate(${position.x}px,${position.y}px)`, transition: "transform 0.1s" }}>
        <div className="relative -translate-x-1/2 -translate-y-1/2 rounded-full border border-white/40"
          style={{ width: isHovering ? "60px" : "32px", height: isHovering ? "60px" : "32px", transition: "width 0.3s,height 0.3s" }} />
      </div>
      <style jsx global>{`@media (min-width: 768px) { * { cursor: none !important; } }`}</style>
    </>
  )
}
