import type { Metadata, Viewport } from 'next';
import { AuthProvider } from '@/lib/auth/auth-context';
import './globals.css';

export const viewport: Viewport = {
  themeColor: '#F0EEEB',
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
        style={{ color: 'var(--text, #1A1814)', background: '#F0EEEB' }}
        suppressHydrationWarning
      >
        {/* ── Flux warm ambient background ── */}
        <div className="flux-bg" aria-hidden="true">
          <div className="flux-blob flux-blob-1" />
          <div className="flux-blob flux-blob-2" />
          <div className="flux-blob flux-blob-3" />
          <div className="flux-blob flux-blob-4" />
        </div>

        {/* All page content sits above the blobs */}
        <div className="flux-content">
          <AuthProvider>
            {children}
          </AuthProvider>
        </div>
      </body>
    </html>
  );
}
