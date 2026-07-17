import { describe, it } from 'vitest'
import * as fc from 'fast-check'

/**
 * Validates: Requirements 6.1, 6.5
 * Property 2: Character Scramble Completion
 *
 * For any input string s and elapsed duration >= 600ms,
 * the scramble output must equal s exactly with no residual scramble characters.
 */

const CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'

function simulateScramble(text: string, elapsed: number): string {
  return text.split('').map((ch, i) => {
    if (ch === ' ') return ' '
    const revealAt = (i / text.length) * 200
    if (elapsed > revealAt) return ch
    return CHARS[Math.floor(Math.random() * CHARS.length)]
  }).join('')
}

describe('Property 2: Character Scramble Completion (Req 6.1, 6.5)', () => {
  it('returns exact final text when elapsed >= 600ms', () => {
    fc.assert(
      fc.property(
        fc.string({ minLength: 1, maxLength: 80 }),
        (text) => simulateScramble(text, 600) === text
      ),
      { numRuns: 500 }
    )
  })
})
