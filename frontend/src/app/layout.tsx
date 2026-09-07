import type { Metadata, Viewport } from 'next';
import { AuthProvider } from '@/lib/auth/auth-context';
import './globals.css';

export const viewport: Viewport = {
  themeColor: '#150E08',
};

export const metadata: Metadata = {
  title: 'Cortex — Engineering Reasoning Engine',
  description: 'Understand Code. Learn Engineering.',
  icons: { icon: '/favicon.ico' },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
    >
      <head>
        {/* Preconnect so fonts load fast when online; silently skipped when offline */}
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        {/* Font stacks — loaded via CSS @import so the build never fails offline */}
        <style dangerouslySetInnerHTML={{ __html: `
          @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;500;600;700;800&family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');
          :root {
            --font-display: 'Syne', system-ui, sans-serif;
            --font-sans:    'Inter', system-ui, -apple-system, sans-serif;
            --font-mono:    'JetBrains Mono', ui-monospace, monospace;
          }
        `}} />
      </head>
      <body
        className="min-h-screen antialiased"
        style={{ color: 'var(--text, #F5EFE7)', background: '#150E08' }}
        suppressHydrationWarning
      >
        {/* ── Deep brown ambient background ── */}
        {/* Lean set of static blurred washes: four corner anchors + three
            roaming pockets. Down from twelve layers to limit compositor cost
            from the `screen` blend + large blur. */}
        <div className="cx-ambient" aria-hidden="true">
          <div className="cx-orb cx-orb-lg cx-orb-1" />
          <div className="cx-orb cx-orb-lg cx-orb-2" />
          <div className="cx-orb cx-orb-lg cx-orb-3" />
          <div className="cx-orb cx-orb-lg cx-orb-4" />
          <div className="cx-orb cx-orb-sm cx-orb-5" />
          <div className="cx-orb cx-orb-sm cx-orb-6" />
          <div className="cx-orb cx-orb-sm cx-orb-9" />
        </div>
        <div className="cx-scrim" aria-hidden="true" />

        {/* All page content sits above the ambient mesh */}
        <div className="cx-content">
          <AuthProvider>
            {children}
          </AuthProvider>
        </div>
      </body>
    </html>
  );
}
