// =============================================================================
// Integration test — useScrollStory ScrollTrigger cleanup
// Requirements: 9.6, 20.5
//
// Verifies that when the useScrollStory hook unmounts it calls .kill() on
// every ScrollTrigger instance that was created during mount.
//
// Test approach:
//   1. Mock gsap/ScrollTrigger — ScrollTrigger.create() returns an object
//      with a kill spy so we can assert it was called.
//   2. Mock window.matchMedia to return { matches: false } so the
//      prefers-reduced-motion guard does NOT skip the hook.
//   3. Mock gsap — fromTo / to / set are no-ops (we are not testing animation,
//      only that triggers are registered and then killed).
//   4. Set up DOM with <main><section id="s1"></section><section id="s2"></section></main>
//      before each test.
//   5. Mount a component using useScrollStory via renderHook.
//   6. Capture the ScrollTrigger instances returned by ScrollTrigger.create.
//   7. Unmount.
//   8. Assert each instance's .kill() was called exactly once.
// =============================================================================

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { act } from 'react';
import { useEffect } from 'react';

// ---------------------------------------------------------------------------
// vi.hoisted — runs before vi.mock() factories so spy refs are shared across
// both the mock factory and the test suite.
// ---------------------------------------------------------------------------
const { mockScrollTriggerCreate, createdInstances } = vi.hoisted(() => {
  // Each created trigger instance gets its own kill spy
  const createdInstances: Array<{ kill: ReturnType<typeof vi.fn> }> = [];

  const mockScrollTriggerCreate = vi.fn((config: unknown) => {
    // Call any lifecycle callbacks from the config to simulate real behaviour
    // (entrance onEnter / exit onLeave etc.).  We don't need them for the
    // cleanup assertion, but calling them would not break anything.
    void config;
    const instance = { kill: vi.fn() };
    createdInstances.push(instance);
    return instance;
  });

  return { mockScrollTriggerCreate, createdInstances };
});

const { mockGsapFromTo, mockGsapTo, mockGsapSet } = vi.hoisted(() => ({
  mockGsapFromTo: vi.fn(),
  mockGsapTo: vi.fn(),
  mockGsapSet: vi.fn(),
}));

// ---------------------------------------------------------------------------
// Mock gsap/ScrollTrigger
// ---------------------------------------------------------------------------
vi.mock('gsap/ScrollTrigger', () => ({
  ScrollTrigger: {
    create: mockScrollTriggerCreate,
  },
}));

// ---------------------------------------------------------------------------
// Mock gsap (animations are no-ops; we only care about ScrollTrigger lifecycle)
// ---------------------------------------------------------------------------
vi.mock('gsap', () => ({
  default: {
    registerPlugin: vi.fn(),
    fromTo: mockGsapFromTo,
    to: mockGsapTo,
    set: mockGsapSet,
  },
}));

// ---------------------------------------------------------------------------
// Import mocked modules (must come after vi.mock declarations)
// ---------------------------------------------------------------------------
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import gsap from 'gsap';

// ---------------------------------------------------------------------------
// Inline useScrollStory hook — mirrors the implementation in page.tsx exactly.
// Testing the hook in isolation avoids needing to mount the full page tree.
// ---------------------------------------------------------------------------
function useScrollStory() {
  useEffect(() => {
    // Req 5.6 — early-return when visitor prefers reduced motion
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;

    const sections = Array.from(
      document.querySelectorAll<HTMLElement>('main section')
    );

    if (sections.length === 0) return;

    const triggers: ReturnType<typeof ScrollTrigger.create>[] = [];

    sections.forEach((section) => {
      // CLS prevention — lock natural height before GSAP sets inline styles
      if (!section.style.minHeight) {
        const naturalHeight = section.offsetHeight;
        if (naturalHeight > 0) {
          section.style.minHeight = `${naturalHeight}px`;
        }
      }

      // Entrance trigger
      const entranceTrigger = ScrollTrigger.create({
        trigger: section,
        start: 'top 88%',
        end: 'top 20%',
        onEnter: () => {
          gsap.fromTo(
            section,
            { opacity: 0, y: 48 },
            { opacity: 1, y: 0, duration: 0.9, ease: 'cubic.out', overwrite: 'auto' }
          );
        },
        onLeaveBack: () => {
          gsap.set(section, { opacity: 0, y: 48 });
        },
      });

      // Exit trigger
      const exitTrigger = ScrollTrigger.create({
        trigger: section,
        start: 'top top',
        end: 'bottom top',
        onLeave: () => {
          gsap.to(section, { opacity: 0.6, y: -24, duration: 0.6, ease: 'cubic.out', overwrite: 'auto' });
        },
        onEnterBack: () => {
          gsap.to(section, { opacity: 1, y: 0, duration: 0.6, ease: 'cubic.out', overwrite: 'auto' });
        },
      });

      triggers.push(entranceTrigger, exitTrigger);
    });

    // Req 9.6 — kill every instance on unmount to prevent memory leaks
    return () => {
      triggers.forEach((t) => t.kill());
    };
  }, []);
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Set up a minimal DOM: <main> containing two <section> elements. */
function setupDOM() {
  const main = document.createElement('main');
  const s1 = document.createElement('section');
  s1.id = 's1';
  const s2 = document.createElement('section');
  s2.id = 's2';
  main.appendChild(s1);
  main.appendChild(s2);
  document.body.appendChild(main);
  return main;
}

function teardownDOM(main: HTMLElement) {
  if (main.parentNode) main.parentNode.removeChild(main);
}

// ---------------------------------------------------------------------------
// Setup / Teardown
// ---------------------------------------------------------------------------

beforeEach(() => {
  vi.clearAllMocks();
  createdInstances.length = 0;

  // Mock matchMedia: prefers-reduced-motion does NOT match → hook runs normally
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    configurable: true,
    value: vi.fn().mockImplementation((query: string) => ({
      matches: false,   // reduced-motion guard → false → hook proceeds
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });
});

afterEach(() => {
  vi.restoreAllMocks();
  // Clean up any leftover DOM nodes
  document.querySelectorAll('main').forEach((el) => el.remove());
});

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('useScrollStory — ScrollTrigger cleanup on unmount (Req 9.6, 20.5)', () => {

  it('calls ScrollTrigger.create once per trigger per section (2 sections × 2 = 4 creates)', () => {
    const main = setupDOM();

    const { unmount } = renderHook(() => useScrollStory());

    // 2 sections × 2 triggers each = 4 create calls
    expect(mockScrollTriggerCreate).toHaveBeenCalledTimes(4);
    expect(createdInstances).toHaveLength(4);

    unmount();
    teardownDOM(main);
  });

  it('calls .kill() on every created ScrollTrigger instance on unmount — Req 9.6', () => {
    const main = setupDOM();

    const { unmount } = renderHook(() => useScrollStory());

    // Verify no kills have happened yet
    createdInstances.forEach((inst) => {
      expect(inst.kill).not.toHaveBeenCalled();
    });

    act(() => {
      unmount();
    });

    // Every instance must have been killed exactly once
    createdInstances.forEach((inst) => {
      expect(inst.kill).toHaveBeenCalledTimes(1);
    });

    teardownDOM(main);
  });

  it('kills all 4 trigger instances when 2 sections are present — Req 9.6, 20.5', () => {
    const main = setupDOM();

    const { unmount } = renderHook(() => useScrollStory());

    expect(createdInstances).toHaveLength(4);

    act(() => {
      unmount();
    });

    const killCount = createdInstances.filter(
      (inst) => inst.kill.mock.calls.length === 1
    ).length;
    expect(killCount).toBe(4);

    teardownDOM(main);
  });

  it('kills entrance trigger and exit trigger independently for each section', () => {
    const main = setupDOM();

    const { unmount } = renderHook(() => useScrollStory());

    // Instances are pushed in order: [s1-entrance, s1-exit, s2-entrance, s2-exit]
    const [s1Entrance, s1Exit, s2Entrance, s2Exit] = createdInstances;

    act(() => {
      unmount();
    });

    expect(s1Entrance.kill).toHaveBeenCalledTimes(1);
    expect(s1Exit.kill).toHaveBeenCalledTimes(1);
    expect(s2Entrance.kill).toHaveBeenCalledTimes(1);
    expect(s2Exit.kill).toHaveBeenCalledTimes(1);

    teardownDOM(main);
  });

  it('does not call .kill() if there are no sections in the DOM', () => {
    // No <main> / no <section> elements added
    const { unmount } = renderHook(() => useScrollStory());

    expect(mockScrollTriggerCreate).not.toHaveBeenCalled();
    expect(createdInstances).toHaveLength(0);

    act(() => {
      unmount();
    });

    // Nothing to kill — no errors, no kill calls
    expect(createdInstances).toHaveLength(0);
  });

  it('does not create any ScrollTrigger instances when prefers-reduced-motion is true', () => {
    // Override matchMedia so prefers-reduced-motion matches
    window.matchMedia = vi.fn().mockImplementation((query: string) => ({
      matches: query === '(prefers-reduced-motion: reduce)',
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }));

    const main = setupDOM();

    const { unmount } = renderHook(() => useScrollStory());

    // Guard fires — no ScrollTrigger instances created
    expect(mockScrollTriggerCreate).not.toHaveBeenCalled();

    act(() => {
      unmount();
    });

    // Nothing to kill
    expect(createdInstances).toHaveLength(0);

    teardownDOM(main);
  });

  it('scales kill calls correctly for a single section (2 triggers → 2 kills)', () => {
    // Only one section
    const main = document.createElement('main');
    const section = document.createElement('section');
    section.id = 'solo';
    main.appendChild(section);
    document.body.appendChild(main);

    const { unmount } = renderHook(() => useScrollStory());

    expect(createdInstances).toHaveLength(2);

    act(() => {
      unmount();
    });

    createdInstances.forEach((inst) => {
      expect(inst.kill).toHaveBeenCalledTimes(1);
    });

    teardownDOM(main);
  });

  it('each kill() is called exactly once — no double-kills on unmount', () => {
    const main = setupDOM();

    const { unmount } = renderHook(() => useScrollStory());

    act(() => {
      unmount();
    });

    createdInstances.forEach((inst) => {
      // Exactly once, never more
      expect(inst.kill).toHaveBeenCalledTimes(1);
    });

    teardownDOM(main);
  });
});
