import type { Metadata, Viewport } from 'next';
import { AuthProvider } from '@/lib/auth/auth-context';
import { AmbientController } from '@/components/layout/AmbientController';
import { AmbientBackground } from '@/components/layout/AmbientBackground';
import './globals.css';

// Set the ambient tier on <html> before first paint so the background never
// flashes the wrong intensity during hydration. Mirrors tierForPath() in
// AmbientController; kept tiny and dependency-free so it can run inline.
const AMBIENT_BOOTSTRAP = `(function(){try{
  var p=location.pathname,t='app';
  if(p==='/'||p.indexOf('/privacy')===0||p.indexOf('/terms')===0){t='landing';}
  else if(p.indexOf('/login')===0||p.indexOf('/signup')===0||p.indexOf('/forgot-password')===0||p.indexOf('/reset-password')===0||p.indexOf('/verify-email')===0){t='calm';}
  document.documentElement.setAttribute('data-ambient',t);
}catch(e){document.documentElement.setAttribute('data-ambient','app');}})();`;

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
      data-ambient="app"
      suppressHydrationWarning
    >
      <head>
        {/* Set the ambient tier before paint to avoid an intensity flash */}
        <script dangerouslySetInnerHTML={{ __html: AMBIENT_BOOTSTRAP }} />
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
        style={{ color: 'var(--text, #F5EFE7)', background: '#080808' }}
        suppressHydrationWarning
      >
        {/* ── Shared ambient background — Apple Music "Replay" style ── */}
        {/* Deep espresso base gradient (pure CSS, always present so there's no
            flash and a graceful fallback when WebGL is unavailable). */}
        <div className="cx-ambient" aria-hidden="true" />
        {/* The living atmosphere: a WebGL fluid-smoke shader whose intensity is
            driven by the data-ambient tier. Mounts client-side over the base;
            silently absent if WebGL is unsupported. See AmbientBackground. */}
        <AmbientBackground />
        {/* Readability scrim sits over the atmosphere so content stays dominant
            and no bright field brightens directly behind text. */}
        <div className="cx-scrim" aria-hidden="true" />

        {/* Keeps data-ambient in sync with the current route */}
        <AmbientController />

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
