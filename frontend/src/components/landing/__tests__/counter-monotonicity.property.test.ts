import { describe, it } from 'vitest'
import * as fc from 'fast-check'

/**
 * Validates: Requirements 4.4, 4.7
 *
 * Pure easing function extracted from AnimatedNumber in About.tsx — cubic-ease-out.
 * Original implementation: Math.round((1 - Math.pow(1 - p, 3)) * value)
 */
function counterValue(t: number, maxValue: number): number {
  return Math.round((1 - Math.pow(1 - t, 3)) * maxValue)
}

describe('Property 1: Counter Monotonicity (Req 4.4, 4.7)', () => {
  it('is monotonically non-decreasing for any t1 ≤ t2', () => {
    fc.assert(
      fc.property(
        fc.float({ min: 0, max: 1, noNaN: true }),
        fc.float({ min: 0, max: 1, noNaN: true }),
        fc.integer({ min: 0, max: 1000 }),
        (a, b, maxValue) => {
          const t1 = Math.min(a, b)
          const t2 = Math.max(a, b)
          return counterValue(t1, maxValue) <= counterValue(t2, maxValue)
        }
      ),
      { numRuns: 1000 }
    )
  })

  it('returns integer values at all times', () => {
    fc.assert(
      fc.property(
        fc.float({ min: 0, max: 1, noNaN: true }),
        fc.integer({ min: 0, max: 1000 }),
        (t, maxValue) => Number.isInteger(counterValue(t, maxValue))
      ),
      { numRuns: 1000 }
    )
  })

  it('starts at 0 and ends at maxValue', () => {
    fc.assert(
      fc.property(
        fc.integer({ min: 0, max: 1000 }),
        (maxValue) =>
          counterValue(0, maxValue) === 0 && counterValue(1, maxValue) === maxValue
      )
    )
  })
})
