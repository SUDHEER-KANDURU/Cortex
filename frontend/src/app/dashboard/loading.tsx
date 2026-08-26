// Dashboard route loading.tsx
// Shown by Next.js App Router while the dashboard JS bundle is being fetched.
// Matches the visual of the inline loader in DashboardPage so there is zero
// visual jump between the two states.

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
        background: 'var(--bg, #EAEAEB)',
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
          background: 'var(--glass-card, rgba(255,255,255,0.92))',
          border: '1px solid var(--border, rgba(0,0,0,0.07))',
          boxShadow: 'var(--shadow-xl, 0 8px 32px rgba(0,0,0,0.11))',
          backdropFilter: 'blur(32px) saturate(180%)',
          WebkitBackdropFilter: 'blur(32px) saturate(180%)',
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
            background: 'var(--primary-dim, rgba(107,143,174,0.12))',
            border: '1px solid var(--border-hover, rgba(0,0,0,0.13))',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <svg width="26" height="26" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path
              d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"
              stroke="var(--primary, #1E2A38)"
              strokeWidth="1.8"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </div>

        {/* Label */}
        <div style={{ textAlign: 'center', display: 'flex', flexDirection: 'column', gap: 6 }}>
          <span
            style={{
              fontFamily: 'Syne, sans-serif',
              fontSize: 15,
              fontWeight: 700,
              letterSpacing: '-0.03em',
              color: 'var(--text, #18181B)',
            }}
          >
            Cortex
          </span>
          <span
            style={{
              fontFamily: '"JetBrains Mono", monospace',
              fontSize: 11,
              letterSpacing: '0.07em',
              color: 'var(--text-muted, #A1A1AA)',
              textTransform: 'uppercase',
            }}
          >
            Loading Dashboard…
          </span>
        </div>

        {/* Progress bar — CSS animation only, no JS */}
        <div
          style={{
            width: '100%',
            height: 2,
            borderRadius: 9999,
            background: 'var(--border, rgba(0,0,0,0.07))',
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
              background: 'var(--primary, #1E2A38)',
              opacity: 0.8,
              animation: 'cortex-bar-sweep 1.8s cubic-bezier(0.4,0,0.2,1) infinite',
            }}
          />
        </div>
      </div>
    </div>
  );
}
