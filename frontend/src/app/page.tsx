'use client'

import { PortfolioHeader }       from "@/components/landing/Header"
import { PortfolioHero }          from "@/components/landing/Hero"
import { PortfolioSelectedWorks } from "@/components/landing/SelectedWorks"
import { PortfolioAbout }         from "@/components/landing/About"
import { PortfolioClientLogos }   from "@/components/landing/ClientLogos"
import { PortfolioTestimonials }  from "@/components/landing/Testimonials"
import { PortfolioAwards }        from "@/components/landing/Awards"
import { PortfolioInsights }      from "@/components/landing/Insights"
import { PortfolioFinalCTA }      from "@/components/landing/FinalCTA"
import { PortfolioFooter }        from "@/components/landing/Footer"
import { GradientBar }            from "@/components/ui/gradient-bar"
import { MagneticCursor }         from "@/components/ui/magnetic-cursor"

export default function HomePage() {
  return (
    <div
      className="portfolio-page"
      style={{ fontFamily: "'Inter Tight', 'Inter', sans-serif" }}
    >
      <MagneticCursor />
      <PortfolioHeader />
      <main>
        <PortfolioHero />
        <PortfolioSelectedWorks />
        <PortfolioAbout />
        <PortfolioClientLogos />
        <PortfolioTestimonials />
        <PortfolioAwards />
        <PortfolioInsights />
        <PortfolioFinalCTA />
      </main>
      <PortfolioFooter />
      <GradientBar />
    </div>
  )
}
