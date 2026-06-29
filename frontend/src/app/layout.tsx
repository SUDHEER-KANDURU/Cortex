// =============================================================================
// Root Layout — Dark background, Inter font, Navbar at the top
// =============================================================================

import type { Metadata } from 'next';
import { Inter } from 'next/font/google';
import './globals.css';
import Navbar from '@/components/layout/Navbar';

const inter = Inter({
  subsets: ['latin'],
  variable: '--font-inter',
  display: 'swap',
});

export const metadata: Metadata = {
  title: 'Cortex — Engineering Reasoning Engine',
  description: 'Understand Code. Learn Engineering.',
  icons: {
    icon: '/favicon.ico',
  },
};

export interface RootLayoutProps {
  children: React.ReactNode;
}

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="en" className={`${inter.variable} dark`} suppressHydrationWarning>
      <body className="min-h-screen bg-gray-950 text-gray-100 antialiased">
        {/* Top navigation */}
        <Navbar />

        {/* Main content area — full height below navbar */}
        <main className="flex min-h-[calc(100vh-3.5rem)] flex-col">
          {children}
        </main>
      </body>
    </html>
  );
}
