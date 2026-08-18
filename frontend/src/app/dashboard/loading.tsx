// Dashboard route loading.tsx
// ──────────────────────────────────────────────────────────────────────────────
// Shown by Next.js App Router while the dashboard JS bundle is being fetched
// (before React hydration). Matches the exact same visual as the inline loader
// in DashboardPage so there is zero visual jump between the two states.
//
// Flow:
//   1. Browser requests /dashboard
//   2. Next.js streams this loading.tsx shell immediately (fast)
//   3. Dashboard JS bundle downloads → React hydrates
//   4. DashboardPage renders with its own initialLoading guard (same visuals)
//   5. Once jobs fetch resolves, initialLoading → false → full UI appears
// ──────────────────────────────────────────────────────────────────────────────

export default function DashboardLoading() {
  return (
    <div
      aria-live="polite"
      aria-busy="true"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 9999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: '#060810',
      }}
    >
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 20,
          padding: '36px 32px',
          borderRadius: 26,
          background: 'rgba(14,18,28,0.88)',
          border: '1px solid rgba(255,255,255,0.07)',
          boxShadow: '0 32px 80px rgba(0,0,0,0.5)',
          backdropFilter: 'blur(32px) saturate(200%)',
          WebkitBackdropFilter: 'blur(32px) saturate(200%)',
          minWidth: 260,
          maxWidth: 360,
        }}
      >
        {/* Cortex icon */}
        <div
          style={{
            width: 56,
            height: 56,
            borderRadius: 16,
            background:
              'radial-gradient(circle at 35% 35%, rgba(0,229,168,0.18) 0%, rgba(108,124,255,0.08) 60%, transparent 100%)',
            border: '1px solid rgba(0,229,168,0.28)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 0 32px rgba(0,229,168,0.12)',
          }}
        >
          <svg width="26" height="26" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path
              d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"
              stroke="#00E5A8"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </div>

        {/* Label */}
        <div
          style={{
            textAlign: 'center',
            display: 'flex',
            flexDirection: 'column',
            gap: 6,
          }}
        >
          <span
            style={{
              fontFamily: 'Syne, sans-serif',
              fontSize: 15,
              fontWeight: 700,
              letterSpacing: '-0.03em',
              color: '#F0F4FF',
            }}
          >
            Cortex
          </span>
          <span
            style={{
              fontFamily: '"JetBrains Mono", monospace',
              fontSize: 11,
              letterSpacing: '0.07em',
              color: '#6E7A90',
              textTransform: 'uppercase',
            }}
          >
            Loading Dashboard…
          </span>
        </div>

        {/* Progress bar — CSS animation, no JS needed in loading.tsx */}
        <div
          style={{
            width: '100%',
            height: 2,
            borderRadius: 9999,
            background: 'rgba(255,255,255,0.06)',
            overflow: 'hidden',
            position: 'relative',
          }}
        >
          <div
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              height: '100%',
              width: '40%',
              borderRadius: 9999,
              background:
                'linear-gradient(90deg, transparent 0%, #00E5A8 50%, transparent 100%)',
              animation: 'cortex-bar-sweep 1.8s cubic-bezier(0.4,0,0.2,1) infinite',
            }}
          />
        </div>
      </div>
    </div>
  );
}
