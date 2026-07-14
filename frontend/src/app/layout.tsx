import type { Metadata } from 'next';
import { Syne, DM_Sans, Fira_Code } from 'next/font/google';
import './globals.css';

// Display / headings — geometric, precise, used by serious engineering products
const syne = Syne({
  subsets: ['latin'],
  variable: '--font-display',
  weight: ['400', '500', '600', '700', '800'],
  display: 'swap',
});

// Body — clean, slightly wider than Inter, not the default everywhere
const dmSans = DM_Sans({
  subsets: ['latin'],
  variable: '--font-sans',
  weight: ['300', '400', '500', '600'],
  display: 'swap',
});

// Monospace — ligature support, warmer than JetBrains Mono
const firaCode = Fira_Code({
  subsets: ['latin'],
  variable: '--font-mono',
  weight: ['400', '500', '600'],
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'Cortex — Engineering Reasoning Engine',
  description: 'Understand Code. Learn Engineering.',
  icons: { icon: '/favicon.ico' },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={`${syne.variable} ${dmSans.variable} ${firaCode.variable} dark`}
      suppressHydrationWarning
    >
      <body className="min-h-screen antialiased" style={{ background: '#000', color: '#fff' }}>
        {children}
      </body>
    </html>
  );
}
