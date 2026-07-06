'use client';

import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '@/lib/utils/cn';

const SECTIONS = [
  { id: 'mission', label: 'Mission' },
  { id: 'engine', label: 'Engine' },
  { id: 'knowledge', label: 'Knowledge' },
  { id: 'insights', label: 'Insights' },
  { id: 'product', label: 'Product' }
];

export default function JourneyNav() {
  const [activeSection, setActiveSection] = useState('hero');
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      const scrollY = window.scrollY;
      const windowHeight = window.innerHeight;

      // Only show after the hero section (Scene 01)
      setIsVisible(scrollY > windowHeight * 0.8);

      // Simple scroll-spy logic
      // In a real implementation, we'd use section offsets
      const sectionElements = SECTIONS.map(s => document.getElementById(s.id));
      const current = sectionElements.reduce((acc, el, i) => {
        if (el && scrollY >= el.offsetTop - 200) {
          return SECTIONS[i].id;
        }
        return acc;
      }, 'hero');

      setActiveSection(current);
    };

    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  return (
    <AnimatePresence>
      {isVisible && (
        <motion.nav
          initial={{ y: -100, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          exit={{ y: -100, opacity: 0 }}
          transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
          className="fixed top-0 left-0 w-full z-[60] px-8 py-4 backdrop-blur-xl border-b border-white/5 flex items-center justify-between"
        >
          <div className="flex items-center gap-4">
            <div className="w-6 h-6 rounded bg-carnallite-violet flex items-center justify-center">
              <div className="w-3 h-3 bg-white rounded-sm rotate-45" />
            </div>
            <span className="font-mono text-[10px] uppercase tracking-[0.3em] font-bold">Cortex // Journey</span>
          </div>

          <div className="hidden md:flex items-center gap-8">
            {SECTIONS.map((section) => (
              <a
                key={section.id}
                href={`#${section.id}`}
                className={cn(
                  "font-mono text-[10px] uppercase tracking-widest transition-colors relative py-2",
                  activeSection === section.id ? "text-white" : "text-white/40 hover:text-white/60"
                )}
              >
                {section.label}
                {activeSection === section.id && (
                  <motion.div
                    layoutId="nav-underline"
                    className="absolute bottom-0 left-0 w-full h-px bg-electric-blue"
                  />
                )}
              </a>
            ))}
          </div>

          <button className="px-4 py-2 bg-white text-black font-mono text-[10px] font-bold rounded-lg uppercase tracking-widest hover:bg-white/90 transition-all">
            Get Cortex
          </button>
        </motion.nav>
      )}
    </AnimatePresence>
  );
}
