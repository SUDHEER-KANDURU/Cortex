"use client"

const techs = [
  "Next.js 14", "TypeScript", "FastAPI", "Python 3.12", "Neo4j 5",
  "PostgreSQL 16", "Celery 5", "Redis 7", "React Flow", "Docker",
  "SQLAlchemy 2", "Pydantic v2", "Alembic", "Uvicorn",
]

export function PortfolioClientLogos() {
  return (
    <section className="py-16 border-border overflow-hidden md:py-10 border-t-[0]">
      <div className="max-w-[1280px] mx-auto px-6 md:px-12 mb-8">
        <p className="text-sm text-muted-foreground text-center">Built on production-grade open-source infrastructure</p>
      </div>

      <div className="relative">
        <div className="flex animate-marquee hover:[animation-play-state:paused]">
          {[...techs, ...techs].map((tech, index) => (
            <div key={`${tech}-${index}`} className="flex items-center justify-center min-w-[200px] px-8">
              <span className="text-2xl md:text-3xl font-semibold text-muted-foreground/50 whitespace-nowrap">
                {tech}
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}
