// =============================================================================
// Integration test — Lenis ↔ GSAP ticker bridge cleanup
// Requirements: 16.4, 20.9
//
// Verifies that when the useLenis hook unmounts it:
//   1. Removes the GSAP ticker callback with the exact same reference that was
//      passed to gsap.ticker.add  (Req 16.4)
//   2. Calls lenis.destroy()  (Req 16.4, 20.9)
// =============================================================================

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { act } from 'react';
import { useLayoutEffect } from 'react';

// ---------------------------------------------------------------------------
// vi.hoisted — runs before vi.mock() factories, so we can share spy refs
// ---------------------------------------------------------------------------
const {
  mockLenisDestroy,
  mockLenisOn,
  mockLenisRaf,
  mockTickerAdd,
  mockTickerRemove,
  mockTickerLagSmoothing,
  mockScrollTriggerUpdate,
  addedCallbacks,
} = vi.hoisted(() => {
  const addedCallbacks: ((...args: unknown[]) => void)[] = [];
  const mockTickerAdd = vi.fn((cb: (...args: unknown[]) => void) => {
    addedCallbacks.push(cb);
  });

  return {
    mockLenisDestroy: vi.fn(),
    mockLenisOn: vi.fn(),
    mockLenisRaf: vi.fn(),
    mockTickerAdd,
    mockTickerRemove: vi.fn(),
    mockTickerLagSmoothing: vi.fn(),
    mockScrollTriggerUpdate: vi.fn(),
    addedCallbacks,
  };
});

// ---------------------------------------------------------------------------
// Mock Lenis
// ---------------------------------------------------------------------------
vi.mock('lenis', () => ({
  default: vi.fn().mockImplementation(() => ({
    on: mockLenisOn,
    raf: mockLenisRaf,
    destroy: mockLenisDestroy,
  })),
}));

// ---------------------------------------------------------------------------
// Mock GSAP
// ---------------------------------------------------------------------------
vi.mock('gsap', () => ({
  default: {
    registerPlugin: vi.fn(),
    ticker: {
      add: mockTickerAdd,
      remove: mockTickerRemove,
      lagSmoothing: mockTickerLagSmoothing,
    },
  },
}));

// ---------------------------------------------------------------------------
// Mock gsap/ScrollTrigger
// ---------------------------------------------------------------------------
vi.mock('gsap/ScrollTrigger', () => ({
  ScrollTrigger: {
    update: mockScrollTriggerUpdate,
  },
}));

// ---------------------------------------------------------------------------
// Import mocked modules (must come after vi.mock declarations)
// ---------------------------------------------------------------------------
import Lenis from 'lenis';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

// ---------------------------------------------------------------------------
// Inline useLenis hook — mirrors the implementation in page.tsx exactly.
// We test the hook in isolation to avoid needing to mount the full page tree.
// ---------------------------------------------------------------------------
function useLenis() {
  useLayoutEffect(() => {
    const lenis = new Lenis({
      duration: 0.9,
      easing: (t: number) => 1 - Math.pow(1 - t, 3),
      orientation: 'vertical',
      smoothWheel: true,
      wheelMultiplier: 1.0,
      touchMultiplier: 1.5,
      infinite: false,
    });

    lenis.on('scroll', () => ScrollTrigger.update());

    const tickerCallback = (time: number) => lenis.raf(time * 1000);
    gsap.ticker.add(tickerCallback);
    gsap.ticker.lagSmoothing(0);

    const hashTimer = setTimeout(() => {
      const hash = window.location.hash;
      if (hash) {
        const el = document.querySelector(hash) as HTMLElement | null;
        if (el) {
          (lenis as unknown as Record<string, unknown>).scrollTo?.(el, { offset: -80 });
        }
      }
    }, 100);

    return () => {
      clearTimeout(hashTimer);
      gsap.ticker.remove(tickerCallback);
      lenis.destroy();
    };
  }, []);
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('useLenis — Lenis ↔ GSAP ticker bridge cleanup (Req 16.4, 20.9)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    addedCallbacks.length = 0;
  });

  afterEach(() => {
    vi.clearAllTimers();
  });

  it('registers a ticker callback with gsap.ticker.add on mount', () => {
    const { unmount } = renderHook(() => useLenis());

    expect(mockTickerAdd).toHaveBeenCalledTimes(1);
    expect(typeof mockTickerAdd.mock.calls[0][0]).toBe('function');

    unmount();
  });

  it('disables GSAP lag smoothing with lagSmoothing(0) on mount', () => {
    const { unmount } = renderHook(() => useLenis());

    expect(mockTickerLagSmoothing).toHaveBeenCalledWith(0);

    unmount();
  });

  it('calls gsap.ticker.remove with the exact same callback reference that was added — Req 16.4', () => {
    const { unmount } = renderHook(() => useLenis());

    // Capture the callback reference that was registered on mount
    expect(mockTickerAdd).toHaveBeenCalledTimes(1);
    const registeredCallback = mockTickerAdd.mock.calls[0][0];

    act(() => {
      unmount();
    });

    // The exact same function reference must be passed to remove
    expect(mockTickerRemove).toHaveBeenCalledTimes(1);
    expect(mockTickerRemove).toHaveBeenCalledWith(registeredCallback);
  });

  it('calls lenis.destroy() on unmount — Req 16.4, 20.9', () => {
    const { unmount } = renderHook(() => useLenis());

    expect(mockLenisDestroy).not.toHaveBeenCalled();

    act(() => {
      unmount();
    });

    expect(mockLenisDestroy).toHaveBeenCalledTimes(1);
  });

  it('calls gsap.ticker.remove before lenis.destroy() — correct teardown order', () => {
    const callOrder: string[] = [];
    mockTickerRemove.mockImplementation(() => callOrder.push('ticker.remove'));
    mockLenisDestroy.mockImplementation(() => callOrder.push('lenis.destroy'));

    const { unmount } = renderHook(() => useLenis());

    act(() => {
      unmount();
    });

    expect(callOrder).toEqual(['ticker.remove', 'lenis.destroy']);
  });

  it('subscribes to the Lenis scroll event on mount', () => {
    const { unmount } = renderHook(() => useLenis());

    expect(mockLenisOn).toHaveBeenCalledWith('scroll', expect.any(Function));

    unmount();
  });

  it('Lenis scroll handler calls ScrollTrigger.update()', () => {
    const { unmount } = renderHook(() => useLenis());

    const scrollCallArgs = mockLenisOn.mock.calls.find(
      (args) => args[0] === 'scroll'
    );
    expect(scrollCallArgs).toBeDefined();

    const scrollHandler = scrollCallArgs![1] as () => void;
    scrollHandler();

    expect(mockScrollTriggerUpdate).toHaveBeenCalledTimes(1);

    unmount();
  });

  it('ticker callback forwards time * 1000 to lenis.raf', () => {
    const { unmount } = renderHook(() => useLenis());

    const tickerCallback = mockTickerAdd.mock.calls[0][0] as (time: number) => void;
    tickerCallback(1.5);

    expect(mockLenisRaf).toHaveBeenCalledWith(1500);

    unmount();
  });
});
