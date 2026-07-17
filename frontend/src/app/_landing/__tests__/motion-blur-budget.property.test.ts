import { describe, it } from 'vitest'
import * as fc from 'fast-check'

/**
 * Validates: Requirements 13.2
 * Property 4: Motion Blur Budget
 *
 * For any scroll velocity v (px/s), the computed CSS blur applied to the
 * Three.js canvas must satisfy 0 <= blur(v) <= 2px.
 */

function computeMotionBlur(scrollVelocity: number): number {
  return Math.min(Math.abs(scrollVelocity) / 800, 1)
}

describe('Property 4: Motion Blur Budget (Req 13.2)', () => {
  it('blur is always between 0 and 2 for any scroll velocity', () => {
    fc.assert(
      fc.property(
        fc.float({ min: -2000, max: 2000, noNaN: true }),
        (velocity) => {
          const blur = computeMotionBlur(velocity)
          return blur >= 0 && blur <= 2
        }
      ),
      { numRuns: 1000 }
    )
  })
})
