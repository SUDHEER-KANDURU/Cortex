// =============================================================================
// Tailwind CSS Configuration — Cortex Premium Design System
// =============================================================================

import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/features/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  // Dark mode removed — light only. Use 'class' as a no-op to satisfy TS type.
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans:    ['var(--font-sans)', 'Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono:    ['var(--font-mono)', 'JetBrains Mono', 'ui-monospace', 'monospace'],
        display: ['var(--font-display)', 'Syne', 'system-ui', 'sans-serif'],
      },
      colors: {
        bg:              'var(--bg)',
        surface:         'var(--surface)',
        card:            'var(--card)',
        border:          'hsl(var(--border-hsl))',
        input:           'hsl(var(--input))',
        ring:            'hsl(var(--ring))',
        background:      'hsl(var(--background))',
        foreground:      'hsl(var(--foreground))',
        primary: {
          DEFAULT:        'hsl(var(--primary-hsl))',
          foreground:     'hsl(var(--primary-foreground))',
        },
        secondary: {
          DEFAULT:        'hsl(var(--secondary))',
          foreground:     'hsl(var(--secondary-foreground))',
        },
        destructive: {
          DEFAULT:        'hsl(var(--destructive))',
          foreground:     'hsl(var(--destructive-foreground))',
        },
        muted: {
          DEFAULT:        'hsl(var(--muted))',
          foreground:     'hsl(var(--muted-foreground))',
        },
        accent: {
          DEFAULT:        'hsl(var(--accent-hsl))',
          foreground:     'hsl(var(--accent-foreground))',
        },
        popover: {
          DEFAULT:        'hsl(var(--popover))',
          foreground:     'hsl(var(--popover-foreground))',
        },
        // Raw brand tokens
        'cortex-slate':   'var(--primary)',
        'cortex-accent':  'var(--accent)',
        'cortex-text':    'var(--text)',
        'cortex-muted':   'var(--text-muted)',
        'cortex-success': 'var(--success)',
        'cortex-warning': 'var(--warning)',
        'cortex-danger':  'var(--danger)',
      },
      borderRadius: {
        sm:   'var(--radius-sm)',
        md:   'var(--radius-md)',
        lg:   'var(--radius-lg)',
        xl:   'var(--radius-xl)',
        '2xl':'var(--radius-xl)',
        full: 'var(--radius-full)',
      },
      boxShadow: {
        sm:   'var(--shadow-sm)',
        md:   'var(--shadow-md)',
        lg:   'var(--shadow-lg)',
        xl:   'var(--shadow-xl)',
        glow: 'var(--shadow-glow)',
      },
      animation: {
        'fade-up':    'fadeUp 0.6s cubic-bezier(0.16,1,0.3,1) both',
        'fade-in':    'fadeIn 0.5s ease both',
        'scale-in':   'scaleIn 0.4s cubic-bezier(0.16,1,0.3,1) both',
        'spin-slow':  'spin 8s linear infinite',
        'pulse-dot':  'pulse-dot 1.8s ease-in-out infinite',
      },
      keyframes: {
        fadeUp:  { from:{opacity:'0',transform:'translateY(20px)'}, to:{opacity:'1',transform:'translateY(0)'} },
        fadeIn:  { from:{opacity:'0'}, to:{opacity:'1'} },
        scaleIn: { from:{opacity:'0',transform:'scale(0.94)'}, to:{opacity:'1',transform:'scale(1)'} },
        'pulse-dot': {
          '0%,100%': {opacity:'1',transform:'scale(1)'},
          '50%':     {opacity:'0.6',transform:'scale(0.85)'},
        },
      },
      backgroundImage: {
        'gradient-radial': 'radial-gradient(var(--tw-gradient-stops))',
      },
      transitionTimingFunction: {
        'spring': 'cubic-bezier(0.16, 1, 0.3, 1)',
      },
    },
  },
  plugins: [],
};

export default config;
