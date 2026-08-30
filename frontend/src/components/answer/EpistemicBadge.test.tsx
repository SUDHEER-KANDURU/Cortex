// =============================================================================
// EpistemicBadge Tests (Req 5.6)
// Verifies the three epistemic tags are visually distinguished in a way that
// does NOT rely on colour alone: each tag renders its own text label, its own
// icon (svg element), and the data-epistemic contract attribute. Also checks
// the accessible name (aria-label/title) is present, and the unexpected-tag
// fallback still surfaces a label + icon.
// =============================================================================

import React from 'react';
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import EpistemicBadge from './EpistemicBadge';
import type { EpistemicTag } from '@/types';

const CASES: { tag: EpistemicTag; label: string }[] = [
  { tag: 'fact', label: 'FACT' },
  { tag: 'inference', label: 'INFERENCE' },
  { tag: 'prediction', label: 'PREDICTION' },
];

describe('EpistemicBadge', () => {
  it.each(CASES)(
    'renders the $label tag with its label, icon, and data-epistemic contract',
    ({ tag, label }) => {
      render(<EpistemicBadge tag={tag} />);

      const badge = screen.getByTestId('epistemic-badge');

      // data-epistemic contract preserved
      expect(badge).toHaveAttribute('data-epistemic', tag);

      // not colour alone: the text label is present
      expect(badge).toHaveTextContent(label);

      // not colour alone: a distinct icon (svg) is rendered inside the badge
      const icon = screen.getByTestId('epistemic-badge-icon');
      expect(icon).toBeInTheDocument();
      expect(icon.tagName.toLowerCase()).toBe('svg');

      // accessible name present for assistive tech
      expect(badge).toHaveAttribute('title');
      expect(badge.getAttribute('aria-label')).toContain(label);
    }
  );

  it('gives each tag a distinct icon (icons are not identical across tags)', () => {
    const iconIdOf = (tag: EpistemicTag) => {
      const { unmount } = render(<EpistemicBadge tag={tag} />);
      const id = screen.getByTestId('epistemic-badge').getAttribute('data-icon');
      unmount();
      return id;
    };

    const factIcon = iconIdOf('fact');
    const inferenceIcon = iconIdOf('inference');
    const predictionIcon = iconIdOf('prediction');

    // All three icon identifiers are present and mutually distinct.
    expect(factIcon).toBeTruthy();
    expect(inferenceIcon).toBeTruthy();
    expect(predictionIcon).toBeTruthy();
    expect(new Set([factIcon, inferenceIcon, predictionIcon]).size).toBe(3);
  });

  it('falls back gracefully for an unexpected tag while still labelling it', () => {
    // Cast through unknown to exercise the runtime fallback path.
    render(<EpistemicBadge tag={'speculation' as unknown as EpistemicTag} />);

    const badge = screen.getByTestId('epistemic-badge');
    expect(badge).toHaveAttribute('data-epistemic', 'speculation');
    expect(badge).toHaveTextContent('SPECULATION');
    expect(screen.getByTestId('epistemic-badge-icon')).toBeInTheDocument();
  });
});
