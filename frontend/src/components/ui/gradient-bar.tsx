"use client"

import { useEffect, useState } from "react"

export function GradientBar() {
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    const section = document.querySelector("#works")
    if (!section) return

    // IntersectionObserver is far cheaper than a scroll listener querying the DOM
    const obs = new IntersectionObserver(
      ([entry]) => setIsVisible(entry.isIntersecting),
      { threshold: 0, rootMargin: "0px 0px 0px 0px" },
    )
    obs.observe(section)
    return () => obs.disconnect()
  }, [])

  return (
    <div
      className="bottom-gradient-bar transition-opacity duration-500"
      style={{ opacity: isVisible ? 1 : 0 }}
    />
  )
}
