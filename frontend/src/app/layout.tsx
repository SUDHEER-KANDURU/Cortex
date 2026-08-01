import type { Metadata, Viewport } from 'next';
import { Syne, DM_Sans, Fira_Code } from 'next/font/google';
import './globals.css';

// =============================================================================
// Fonts — all available in next/font/google for Next.js 14.2.x
//
// --font-display : Syne     — geometric, precise, used for headings
// --font-sans    : DM Sans  — clean body font
// --font-mono    : Fira Code — ligature mono for code/terminals
// =============================================================================

const syne = Syne({
  subsets: ['latin'],
  variable: '--font-display',
  weight: ['400', '500', '600', '700', '800'],
  display: 'swap',
});

const dmSans = DM_Sans({
  subsets: ['latin'],
  variable: '--font-sans',
  weight: ['300', '400', '500', '600'],
  display: 'swap',
});

const firaCode = Fira_Code({
  subsets: ['latin'],
  variable: '--font-mono',
  weight: ['400', '500', '600'],
  display: 'swap',
});

export const viewport: Viewport = {
  themeColor: '#07090d',
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
      className={`${syne.variable} ${dmSans.variable} ${firaCode.variable} dark`}
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
        style={{ background: 'var(--bg, #07090d)', color: 'var(--text, #FFFFFF)' }}
      >
        {children}
      </body>
    </html>
  );
}
