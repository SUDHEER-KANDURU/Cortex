"use client"

import { useEffect, useState } from "react"

export function GradientBar() {
  const [isVisible, setIsVisible] = useState(false)

  useEffect(() => {
    const handleScroll = () => {
      const section = document.querySelector("#works")
      if (section) {
        const rect = section.getBoundingClientRect()
        setIsVisible(rect.top < window.innerHeight && rect.bottom > 0)
      }
    }
    handleScroll()
    window.addEventListener("scroll", handleScroll)
    return () => window.removeEventListener("scroll", handleScroll)
  }, [])

  return (
    <div
      className="bottom-gradient-bar transition-opacity duration-500"
      style={{ opacity: isVisible ? 1 : 0 }}
    />
  )
}
