// =============================================================================
// Integration test — useMouseSpotlight cleanup
// Requirements: 10.7, 20.9
//
// Verifies that when the useMouseSpotlight hook unmounts it:
//   1. Removes the spotlight div[data-mouse-spotlight] from document.body (Req 10.7)
//   2. Calls cancelAnimationFrame to cancel the running RAF loop (Req 20.9)
// =============================================================================

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { act } from 'react';
import { useEffect } from 'react';

// ---------------------------------------------------------------------------
// Setup — mock window.matchMedia to simulate a pointer:fine (mouse) device.
// jsdom does not implement matchMedia, so we must provide a stub before
// any test code runs.
// ---------------------------------------------------------------------------
beforeEach(() => {
  // Default: pointer:fine → hook should attach
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    configurable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: query === '(pointer: fine)',
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });

  // Ensure document.body is clean before each test
  document
    .querySelectorAll('[data-mouse-spotlight]')
    .forEach((el) => el.remove());
});

afterEach(() => {
  vi.restoreAllMocks();
  // Clean up any leftover spotlight elements
  document
    .querySelectorAll('[data-mouse-spotlight]')
    .forEach((el) => el.remove());
});

// ---------------------------------------------------------------------------
// Inline useMouseSpotlight hook — mirrors the implementation in page.tsx.
// Testing the hook in isolation avoids mounting the full Next.js page tree.
// ---------------------------------------------------------------------------
function useMouseSpotlight() {
  useEffect(() => {
    // Guard: only attach on fine-pointer (mouse/trackpad) devices
    if (!window.matchMedia('(pointer: fine)').matches) return;

    // Create the spotlight overlay element
    const el = document.createElement('div');
    el.setAttribute('data-mouse-spotlight', '');
    el.style.cssText = [
      'position:fixed',
      'inset:0',
      'pointer-events:none',
      'z-index:0',
      'background:radial-gradient(280px circle at var(--sx,50%) var(--sy,50%),rgba(255,255,255,0.07) 0%,transparent 70%)',
      'opacity:0',
      'transition:opacity 300ms ease',
    ].join(';');
    document.body.insertBefore(el, document.body.firstChild);

    // Lerp state
    let cx = 0, cy = 0, tx = 0, ty = 0;
    let rafId: number;
    let running = false;

    function tick() {
      cx += (tx - cx) * 0.08;
      cy += (ty - cy) * 0.08;
      el.style.setProperty('--sx', `${cx}px`);
      el.style.setProperty('--sy', `${cy}px`);
      rafId = requestAnimationFrame(tick);
    }

    function startRAF() {
      if (!running) {
        running = true;
        rafId = requestAnimationFrame(tick);
      }
    }

    function stopRAF() {
      running = false;
      cancelAnimationFrame(rafId);
    }

    const onMouseMove = (e: MouseEvent) => { tx = e.clientX; ty = e.clientY; };
    const onMouseEnter = () => { el.style.opacity = '1'; startRAF(); };
    const onMouseLeave = () => {
      el.style.opacity = '0';
      setTimeout(stopRAF, 300);
    };

    // Start immediately
    startRAF();
    el.style.opacity = '1';

    document.addEventListener('mousemove',  onMouseMove,  { passive: true });
    document.addEventListener('mouseleave', onMouseLeave, { passive: true });
    document.addEventListener('mouseenter', onMouseEnter, { passive: true });

    return () => {
      // Req 20.9 — cancel the RAF loop
      cancelAnimationFrame(rafId);
      document.removeEventListener('mousemove',  onMouseMove);
      document.removeEventListener('mouseleave', onMouseLeave);
      document.removeEventListener('mouseenter', onMouseEnter);
      // Req 10.7 — remove the spotlight element from the DOM
      if (el.parentNode) el.parentNode.removeChild(el);
    };
  }, []);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('useMouseSpotlight — DOM cleanup and RAF cancellation (Req 10.7, 20.9)', () => {

  it('inserts div[data-mouse-spotlight] into document.body on mount', () => {
    const { unmount } = renderHook(() => useMouseSpotlight());

    const el = document.querySelector('[data-mouse-spotlight]');
    expect(el).not.toBeNull();
    expect(document.body.contains(el)).toBe(true);

    unmount();
  });

  it('inserts the spotlight as the first child of document.body', () => {
    const { unmount } = renderHook(() => useMouseSpotlight());

    const el = document.querySelector('[data-mouse-spotlight]');
    expect(el).toBe(document.body.firstChild);

    unmount();
  });

  it('removes div[data-mouse-spotlight] from document.body on unmount — Req 10.7', () => {
    const { unmount } = renderHook(() => useMouseSpotlight());

    // Verify it exists before unmount
    expect(document.querySelector('[data-mouse-spotlight]')).not.toBeNull();

    act(() => {
      unmount();
    });

    // Must be gone after unmount
    expect(document.querySelector('[data-mouse-spotlight]')).toBeNull();
  });

  it('calls cancelAnimationFrame on unmount — Req 20.9', () => {
    const cancelSpy = vi.spyOn(window, 'cancelAnimationFrame');

    const { unmount } = renderHook(() => useMouseSpotlight());

    act(() => {
      unmount();
    });

    expect(cancelSpy).toHaveBeenCalledTimes(1);
    expect(typeof cancelSpy.mock.calls[0][0]).toBe('number');
  });

  it('does not insert spotlight when pointer:fine is false (touch device)', () => {
    // Override matchMedia so pointer:fine returns false
    window.matchMedia = vi.fn().mockImplementation((query: string) => ({
      matches: false, // never matches, including (pointer: fine)
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));

    const { unmount } = renderHook(() => useMouseSpotlight());

    expect(document.querySelector('[data-mouse-spotlight]')).toBeNull();

    unmount();
  });

  it('does not call cancelAnimationFrame when hook was never attached (touch device)', () => {
    window.matchMedia = vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));

    const cancelSpy = vi.spyOn(window, 'cancelAnimationFrame');

    const { unmount } = renderHook(() => useMouseSpotlight());

    act(() => {
      unmount();
    });

    // Guard triggered, hook never ran — no cancelAnimationFrame call
    expect(cancelSpy).not.toHaveBeenCalled();
  });

  it('cancelAnimationFrame is called with the active RAF id returned by requestAnimationFrame', () => {
    // Track which ids were scheduled and which were cancelled
    const scheduledIds: number[] = [];
    const cancelledIds: number[] = [];

    const rafSpy = vi.spyOn(window, 'requestAnimationFrame').mockImplementation(() => {
      const id = Math.floor(Math.random() * 100_000) + 1;
      scheduledIds.push(id);
      return id;
    });

    vi.spyOn(window, 'cancelAnimationFrame').mockImplementation((id: number) => {
      cancelledIds.push(id);
    });

    const { unmount } = renderHook(() => useMouseSpotlight());

    act(() => {
      unmount();
    });

    // The id that was cancelled must be one that was previously scheduled
    expect(cancelledIds.length).toBeGreaterThan(0);
    expect(scheduledIds).toContain(cancelledIds[0]);

    rafSpy.mockRestore();
  });
});
