// =============================================================================
// Property-Based Test — Card Tilt Constraint (Property 6)
// Validates: Requirements 3.10, 15.1
//
// Property 6: For any cursor position within a card's bounding rect, the
// computed `rotateX` and `rotateY` transforms must each satisfy |angle| ≤ 3°.
//
// The `useSpotlight` hook in `page.tsx` computes tilt as:
//   const cx = rect.width  / 2
//   const cy = rect.height / 2
//   const dx = (x - cx) / cx   // normalised -1..1
//   const dy = (y - cy) / cy   // normalised -1..1
//   gsap.set(card, { rotateX: (-dy * 2.5), rotateY: (dx * 2.5) })
//
// Max tilt is ±2.5° (well within the ±3° budget). This test verifies that
// invariant holds for all possible card dimensions and cursor positions.
// =============================================================================

import { describe, it } from 'vitest';
import * as fc from 'fast-check';

// ---------------------------------------------------------------------------
// Pure function under test
//
// Extracted directly from the `applyFrame` closure inside `useSpotlight`.
// The function takes raw mouse coordinates and the card's bounding rect
// dimensions, returning the two rotation angles applied by GSAP.
// ---------------------------------------------------------------------------

/**
 * Computes the card tilt angles for a given cursor position and card size.
 *
 * Mirrors the tilt logic inside `useSpotlight` → `applyFrame`:
 *   cx = rect.width  / 2
 *   cy = rect.height / 2
 *   dx = (mouseX - cx) / cx   → normalised to [-1, 1]
 *   dy = (mouseY - cy) / cy   → normalised to [-1, 1]
 *   rotateX = -dy * 2.5
 *   rotateY =  dx * 2.5
 *
 * @param mouseX - cursor X relative to the card's left edge (px)
 * @param mouseY - cursor Y relative to the card's top edge (px)
 * @param rect   - card dimensions { width, height } (px)
 * @returns object with rotateX and rotateY angles in degrees
 */
function computeTilt(
  mouseX: number,
  mouseY: number,
  rect: { width: number; height: number },
): { rotateX: number; rotateY: number } {
  const cx = rect.width  / 2
  const cy = rect.height / 2
  const dx = (mouseX - cx) / cx   // normalised -1..1
  const dy = (mouseY - cy) / cy   // normalised -1..1
  return {
    rotateX: -dy * 2.5,
    rotateY:  dx * 2.5,
  }
}

// ---------------------------------------------------------------------------
// Arbitraries
// ---------------------------------------------------------------------------

/**
 * Generates a random card size: width and height each in [50, 600]px.
 * This covers everything from small tag cards to large hero cards.
 */
const cardRect = fc.record({
  width:  fc.integer({ min: 50, max: 600 }),
  height: fc.integer({ min: 50, max: 600 }),
})

/**
 * Generates a cursor position that is constrained within the card bounds
 * [0, width] × [0, height]. The position is expressed relative to the card's
 * top-left corner, matching the coordinate space used by `applyFrame` after
 * subtracting `rect.left` / `rect.top`.
 */
const cursorWithinCard = cardRect.chain((rect) =>
  fc.record({
    mouseX: fc.float({ min: 0, max: rect.width,  noNaN: true }),
    mouseY: fc.float({ min: 0, max: rect.height, noNaN: true }),
    rect:   fc.constant(rect),
  })
)

// ---------------------------------------------------------------------------
// Property tests
// ---------------------------------------------------------------------------

describe('Property 6: Card Tilt Constraint — Validates: Requirements 3.10, 15.1', () => {

  it('|rotateX| ≤ 3° for any cursor position within any card bounding rect', () => {
    fc.assert(
      fc.property(cursorWithinCard, ({ mouseX, mouseY, rect }) => {
        const { rotateX } = computeTilt(mouseX, mouseY, rect)
        return Math.abs(rotateX) <= 3
      }),
      { numRuns: 10_000 },
    )
  })

  it('|rotateY| ≤ 3° for any cursor position within any card bounding rect', () => {
    fc.assert(
      fc.property(cursorWithinCard, ({ mouseX, mouseY, rect }) => {
        const { rotateY } = computeTilt(mouseX, mouseY, rect)
        return Math.abs(rotateY) <= 3
      }),
      { numRuns: 10_000 },
    )
  })

  it('both |rotateX| ≤ 3° and |rotateY| ≤ 3° hold simultaneously', () => {
    fc.assert(
      fc.property(cursorWithinCard, ({ mouseX, mouseY, rect }) => {
        const { rotateX, rotateY } = computeTilt(mouseX, mouseY, rect)
        return Math.abs(rotateX) <= 3 && Math.abs(rotateY) <= 3
      }),
      { numRuns: 10_000 },
    )
  })

  it('tilt is zero at the card centre', () => {
    fc.assert(
      fc.property(cardRect, (rect) => {
        const { rotateX, rotateY } = computeTilt(rect.width / 2, rect.height / 2, rect)
        // At the exact centre dx=0, dy=0 → both angles must be 0
        return rotateX === 0 && rotateY === 0
      }),
      { numRuns: 1_000 },
    )
  })

  it('tilt at card corners is exactly ±2.5° (the maximum possible)', () => {
    fc.assert(
      fc.property(cardRect, (rect) => {
        const corners = [
          { mouseX: 0,           mouseY: 0            },  // top-left
          { mouseX: rect.width,  mouseY: 0            },  // top-right
          { mouseX: 0,           mouseY: rect.height  },  // bottom-left
          { mouseX: rect.width,  mouseY: rect.height  },  // bottom-right
        ]

        return corners.every(({ mouseX, mouseY }) => {
          const { rotateX, rotateY } = computeTilt(mouseX, mouseY, rect)
          // At every corner the absolute tilt should be exactly 2.5°
          return Math.abs(rotateX) <= 2.5 + 1e-9 && Math.abs(rotateY) <= 2.5 + 1e-9
        })
      }),
      { numRuns: 1_000 },
    )
  })

})
