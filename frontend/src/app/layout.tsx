import type { Metadata, Viewport } from 'next';
import { Syne, Inter, JetBrains_Mono } from 'next/font/google';
import './globals.css';

// =============================================================================
// Fonts — Premium Liquid Glass type system
//
// --font-display : Syne          — geometric, precise, used for hero headings
// --font-sans    : Inter         — highly legible body + UI font (Apple-grade)
// --font-mono    : JetBrains Mono — clear, readable monospace for code & terminals
// =============================================================================

const syne = Syne({
  subsets: ['latin'],
  variable: '--font-display',
  weight: ['400', '500', '600', '700', '800'],
  display: 'swap',
});

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-sans',
  weight: ['300', '400', '500', '600', '700'],
  display: 'swap',
});

const jetbrainsMono = JetBrains_Mono({
  subsets: ['latin'],
  variable: '--font-mono',
  weight: ['400', '500', '600'],
  display: 'swap',
});

export const viewport: Viewport = {
  themeColor: '#060810',
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
      data-theme="dark"
      className={`${syne.variable} ${inter.variable} ${jetbrainsMono.variable} dark`}
      suppressHydrationWarning
    >
      {/*
        Inline theme script — runs before first paint.
        Reads localStorage and sets data-theme immediately so the browser
        doesn't render a flash before React hydrates.
      */}
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `
              try {
                var t = localStorage.getItem('cortex-theme') || 'dark';
                document.documentElement.setAttribute('data-theme', t);
                document.documentElement.classList.toggle('dark', t === 'dark');
              } catch(e) {}
            `,
          }}
        />
      </head>
      <body
        className="min-h-screen antialiased"
        style={{ color: 'var(--text, #FFFFFF)' }}
        suppressHydrationWarning
      >
        {/* ── Global liquid-blob background — fixed, covers every page ── */}
        <div className="liquid-bg-mesh" aria-hidden="true">
          <div className="liquid-blob liquid-blob-1" />
          <div className="liquid-blob liquid-blob-2" />
          <div className="liquid-blob liquid-blob-3" />
        </div>

        {/* All page content sits above the blobs */}
        <div style={{ position: 'relative', zIndex: 1 }}>
          {children}
        </div>
      </body>
    </html>
  );
}

