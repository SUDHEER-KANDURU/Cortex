"use client"

import type React from "react"
import { useEffect, useRef, useState } from "react"

interface SectionTitleProps {
  children: React.ReactNode
  className?: string
}

export function SectionTitle({ children, className = "" }: SectionTitleProps) {
  const [isVisible, setIsVisible] = useState(false)
  const titleRef = useRef<HTMLHeadingElement>(null)

  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting && !isVisible) setIsVisible(true)
        })
      },
      { threshold: 0.3 },
    )
    if (titleRef.current) observer.observe(titleRef.current)
    return () => observer.disconnect()
  }, [isVisible])

  return (
    <h2
      ref={titleRef}
      className={`overflow-visible text-4xl ${className} ${isVisible ? "section-title-animate" : "opacity-0"}`}
    >
      {children}
    </h2>
  )
}
