'use client';

/**
 * LegalModal — Full-screen overlay modal for Terms/Privacy content.
 * Centered, properly styled with the Cortex glass design system.
 */

import React, { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X } from 'lucide-react';
import { createPortal } from 'react-dom';

interface LegalModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
}

export function LegalModal({ open, onClose, title, children }: LegalModalProps) {
  const contentRef = useRef<HTMLDivElement>(null);

  // Lock body scroll when open
  useEffect(() => {
    if (open) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => { document.body.style.overflow = ''; };
  }, [open]);

  // Close on Escape key
  useEffect(() => {
    if (!open) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [open, onClose]);

  // Scroll content to top when opened
  useEffect(() => {
    if (open && contentRef.current) {
      contentRef.current.scrollTop = 0;
    }
  }, [open]);

  const modalContent = (
    <AnimatePresence>
      {open && (
        <div className="fixed inset-0 z-[9999] flex items-center justify-center p-4 sm:p-6">
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="absolute inset-0"
            style={{ background: 'rgba(8, 5, 3, 0.72)', backdropFilter: 'blur(8px)' }}
            onClick={onClose}
            aria-hidden="true"
          />

          {/* Modal Panel */}
          <motion.div
            initial={{ opacity: 0, scale: 0.92, y: 24 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.92, y: 24 }}
            transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
            className="relative w-full max-w-2xl max-h-[80vh] flex flex-col rounded-2xl overflow-hidden"
            style={{
              background: 'var(--glass-modal)',
              backdropFilter: 'blur(48px) saturate(160%)',
              WebkitBackdropFilter: 'blur(48px) saturate(160%)',
              border: '1px solid rgba(255, 255, 255, 0.14)',
              boxShadow: '0 30px 70px rgba(0, 0, 0, 0.55), inset 0 1.5px 1px rgba(255, 255, 255, 0.34)',
            }}
            role="dialog"
            aria-modal="true"
            aria-label={title}
          >
            {/* Header */}
            <div className="flex items-center justify-between px-6 sm:px-8 py-5 shrink-0"
              style={{ borderBottom: '1px solid var(--border)' }}
            >
              <h2
                className="text-xl font-bold tracking-[-0.02em]"
                style={{ color: 'var(--text)', fontFamily: 'var(--font-display, system-ui)' }}
              >
                {title}
              </h2>
              <button
                type="button"
                onClick={onClose}
                className="w-9 h-9 flex items-center justify-center rounded-full transition-all duration-150 hover:bg-white/10 active:scale-95"
                style={{ color: 'var(--text-muted)' }}
                aria-label="Close"
              >
                <X size={20} strokeWidth={2} />
              </button>
            </div>

            {/* Scrollable Content */}
            <div
              ref={contentRef}
              className="flex-1 overflow-y-auto px-6 sm:px-8 py-6"
              style={{ scrollbarWidth: 'thin', scrollbarColor: 'rgba(255,255,255,0.16) transparent' }}
            >
              {children}
            </div>

            {/* Footer */}
            <div
              className="flex justify-end px-6 sm:px-8 py-4 shrink-0"
              style={{ borderTop: '1px solid var(--border)', background: 'rgba(255,255,255,0.03)' }}
            >
              <button
                type="button"
                onClick={onClose}
                className="px-6 py-2.5 text-sm font-semibold rounded-lg transition-all duration-150 hover:opacity-90 active:scale-[0.97]"
                style={{
                  background: 'var(--primary)',
                  color: 'var(--on-primary)',
                }}
              >
                Got it
              </button>
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );

  // Portal to body to avoid z-index/overflow issues from parent containers
  if (typeof window === 'undefined') return null;
  return createPortal(modalContent, document.body);
}
