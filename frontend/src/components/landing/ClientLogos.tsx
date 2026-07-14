"use client"

const techs = [
  "Next.js 14", "TypeScript", "FastAPI", "Python 3.12", "Neo4j 5",
  "PostgreSQL 16", "Celery 5", "Redis 7", "React Flow", "Docker",
  "SQLAlchemy 2", "Pydantic v2", "Alembic", "Uvicorn",
]

export function PortfolioClientLogos() {
  return (
    <section className="py-16 overflow-hidden relative" style={{ borderTop: "1px solid rgba(255,255,255,0.65)" }}>

      {/* Liquid glass frosted strip behind the text */}
      <div style={{
        position: "absolute", inset: 0,
        background: "rgba(255,255,255,0.5)",
        backdropFilter: "blur(12px) saturate(160%)",
        WebkitBackdropFilter: "blur(12px) saturate(160%)",
        borderTop: "1px solid rgba(255,255,255,0.7)",
        borderBottom: "1px solid rgba(255,255,255,0.7)",
        boxShadow: "inset 0 1px 0 rgba(255,255,255,0.9), inset 0 -1px 0 rgba(0,0,0,0.04)",
        pointerEvents: "none",
      }} />

      <div className="max-w-[1280px] mx-auto px-6 md:px-12 mb-8 relative">
        <p style={{
          fontSize: "11px", fontWeight: 600,
          letterSpacing: "0.12em", textTransform: "uppercase",
          color: "rgba(0,0,0,0.35)", textAlign: "center",
          fontFamily: "var(--font-mono,'Fira Code',monospace)",
        }}>
          Built on production-grade open-source infrastructure
        </p>
      </div>

      {/* Edge fade masks */}
      <div style={{
        position: "absolute", inset: 0, pointerEvents: "none", zIndex: 5,
        background: "linear-gradient(to right, rgba(255,255,255,0.95) 0%, transparent 8%, transparent 92%, rgba(255,255,255,0.95) 100%)",
      }} />

      <div className="relative">
        <div className="flex animate-marquee hover:[animation-play-state:paused]">
          {[...techs, ...techs].map((tech, index) => (
            <div key={`${tech}-${index}`} className="flex items-center justify-center min-w-[180px] px-6">
              <span style={{
                fontSize: "clamp(13px,1.5vw,18px)",
                fontWeight: 600,
                color: "rgba(0,0,0,0.22)",
                whiteSpace: "nowrap",
                fontFamily: "var(--font-mono,'Fira Code',monospace)",
                letterSpacing: "0.02em",
                transition: "color 0.2s ease",
              }}
                onMouseEnter={e => (e.currentTarget.style.color = "rgba(0,0,0,0.7)")}
                onMouseLeave={e => (e.currentTarget.style.color = "rgba(0,0,0,0.22)")}>
                {tech}
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
