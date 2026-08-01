"use client"

const techs = [
  "Next.js 14","TypeScript","FastAPI","Python 3.12","Neo4j 5",
  "PostgreSQL 16","Celery 5","Redis 7","React Flow","Docker",
  "SQLAlchemy 2","Pydantic v2","Alembic","Uvicorn",
]

export function PortfolioClientLogos() {
  return (
    <section className="py-16 overflow-hidden relative" style={{ borderTop: "1px solid var(--cx-card-border)" }}>

      {/* Frosted strip */}
      <div style={{
        position: "absolute", inset: 0, pointerEvents: "none",
        background: "rgba(255,255,255,0.04)",
        backdropFilter: "blur(20px) saturate(200%)",
        WebkitBackdropFilter: "blur(20px) saturate(200%)",
        borderTop: "1px solid var(--cx-card-border)",
        borderBottom: "1px solid var(--cx-card-border)",
      }} />

      <div className="max-w-[1280px] mx-auto px-6 md:px-12 mb-8 relative">
        <p className="cx-eyebrow" style={{ fontSize: "11px", fontWeight: 600, letterSpacing: "0.12em", textTransform: "uppercase", textAlign: "center", fontFamily: "var(--font-mono,'Fira Code',monospace)" }}>
          Built on production-grade open-source infrastructure
        </p>
      </div>

      {/* Edge fades */}
      <div aria-hidden="true" style={{ position: "absolute", inset: 0, pointerEvents: "none", zIndex: 5, background: "linear-gradient(to right, var(--bg) 0%, transparent 8%, transparent 92%, var(--bg) 100%)" }} />

      <div className="relative">
        <div className="flex animate-marquee hover:[animation-play-state:paused]">
          {[...techs, ...techs].map((tech, index) => (
            <div key={`${tech}-${index}`} className="flex items-center justify-center min-w-[180px] px-6">
              <span className="cx-text-faint" style={{ fontSize: "clamp(13px,1.5vw,18px)", fontWeight: 600, whiteSpace: "nowrap", fontFamily: "var(--font-mono,'Fira Code',monospace)", letterSpacing: "0.02em", transition: "color 0.2s ease" }}
                onMouseEnter={e => ((e.currentTarget as HTMLElement).style.color = "var(--cx-text)")}
                onMouseLeave={e => ((e.currentTarget as HTMLElement).style.color = "")}>
                {tech}
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
