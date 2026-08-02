'use client';

import { useEffect, useState } from 'react';
import { cn } from '@/lib/utils/cn';

const SECTIONS = [
  { id: 'mission', label: 'Mission' },
  { id: 'engine', label: 'Engine' },
  { id: 'knowledge', label: 'Knowledge' },
  { id: 'insights', label: 'Insights' },
  { id: 'product', label: 'Product' },
];

export default function JourneyNav() {
  const [activeSection, setActiveSection] = useState('hero');
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    // Visibility: show after user scrolls past 80% of the first viewport
    const visibilityObs = new IntersectionObserver(
      ([entry]) => setIsVisible(!entry.isIntersecting),
      { threshold: 0.2 },
    );
    // Observe the hero section (or body as fallback)
    const heroEl = document.getElementById('hero') ?? document.body.firstElementChild;
    if (heroEl) visibilityObs.observe(heroEl);

    // Active section: one observer per section, much cheaper than scroll listener
    const sectionObs = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            setActiveSection(entry.target.id);
          }
        });
      },
      { threshold: 0.4 },
    );

    SECTIONS.forEach(({ id }) => {
      const el = document.getElementById(id);
      if (el) sectionObs.observe(el);
    });

    return () => {
      visibilityObs.disconnect();
      sectionObs.disconnect();
    };
  }, []);

  if (!isVisible) return null;

  return (
    <nav
      className="fixed top-0 left-0 w-full z-[60] px-8 py-4 backdrop-blur-xl border-b border-white/5 flex items-center justify-between"
      style={{
        // CSS animation instead of framer-motion to avoid the library cost
        animation: 'journeyNavIn 0.5s cubic-bezier(0.16, 1, 0.3, 1) both',
      }}
    >
      <style dangerouslySetInnerHTML={{ __html: `
        @keyframes journeyNavIn {
          from { transform: translateY(-100%); opacity: 0; }
          to   { transform: translateY(0);     opacity: 1; }
        }
      ` }} />

      <div className="flex items-center gap-4">
        <div className="w-6 h-6 rounded bg-carnallite-violet flex items-center justify-center">
          <div className="w-3 h-3 bg-white rounded-sm rotate-45" />
        </div>
        <span className="font-mono text-[10px] uppercase tracking-[0.3em] font-bold">
          Cortex // Journey
        </span>
      </div>

      <div className="hidden md:flex items-center gap-8">
        {SECTIONS.map((section) => (
          <a
            key={section.id}
            href={`#${section.id}`}
            className={cn(
              'font-mono text-[10px] uppercase tracking-widest transition-colors relative py-2',
              activeSection === section.id
                ? 'text-white'
                : 'text-white/40 hover:text-white/60',
            )}
          >
            {section.label}
            {activeSection === section.id && (
              <span className="absolute bottom-0 left-0 w-full h-px bg-electric-blue" />
            )}
          </a>
        ))}
      </div>

      <button className="px-4 py-2 bg-white text-black font-mono text-[10px] font-bold rounded-lg uppercase tracking-widest hover:bg-white/90 transition-all">
        Get Cortex
      </button>
    </nav>
  );
}
