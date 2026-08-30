// =============================================================================
// AnswerRenderer Tests
// Renders a sample CortexAnswer and asserts the shared renderer surfaces every
// part of the contract: title/summary, sections + claims, per-claim epistemic
// badges, clickable evidence chips, confidence/coverage banner, and next-action
// buttons — with callbacks firing on interaction.
// =============================================================================

import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import AnswerRenderer from './AnswerRenderer';
import type { CortexAnswer } from '@/types';

const SAMPLE: CortexAnswer = {
  intent: 'module_breakdown',
  title: 'Module Breakdown',
  summary: 'This service is organized into three cohesive modules.',
  confidence: 0.82,
  coverage_note: 'Analyzed 48 of 50 files; 2 files skipped.',
  sections: [
    {
      heading: 'Modules',
      claims: [
        {
          text: 'The auth module handles login and token issuance.',
          epistemic: 'fact',
          evidence: [
            { file_path: 'src/auth/service.py', line_start: 10, line_end: 42, node_id: 'n1' },
          ],
        },
        {
          text: 'This module likely owns session lifecycle concerns.',
          epistemic: 'inference',
          evidence: [
            { file_path: 'src/auth/session.py', line_start: 5, line_end: null, node_id: 'n2' },
          ],
        },
      ],
    },
    {
      heading: 'Risks',
      claims: [
        {
          text: 'Changing the token schema would ripple into the API layer.',
          epistemic: 'prediction',
          evidence: [
            { file_path: 'src/api/routes.py', line_start: null, line_end: null, node_id: 'n3' },
          ],
        },
      ],
    },
  ],
  next_actions: [
    { label: 'Open auth service', kind: 'open_file', target: 'src/auth/service.py', line_start: 10, line_end: 42 },
    { label: 'Ask about sessions', kind: 'ask_question', target: 'How are sessions expired?', line_start: null, line_end: null },
  ],
};

describe('AnswerRenderer', () => {
  it('renders the title, summary, sections and every claim', () => {
    render(<AnswerRenderer answer={SAMPLE} />);

    expect(screen.getByTestId('answer-title')).toHaveTextContent('Module Breakdown');
    expect(screen.getByTestId('answer-summary')).toHaveTextContent(
      'This service is organized into three cohesive modules.'
    );

    const sections = screen.getAllByTestId('answer-section');
    expect(sections).toHaveLength(2);
    expect(sections[0]).toHaveTextContent('Modules');
    expect(sections[1]).toHaveTextContent('Risks');

    const claims = screen.getAllByTestId('claim');
    expect(claims).toHaveLength(3);
    expect(claims[0]).toHaveTextContent('The auth module handles login and token issuance.');
  });

  it('renders a distinct epistemic badge for each claim', () => {
    render(<AnswerRenderer answer={SAMPLE} />);

    const badges = screen.getAllByTestId('epistemic-badge');
    expect(badges).toHaveLength(3);

    const tags = badges.map((b) => b.getAttribute('data-epistemic'));
    expect(tags).toEqual(['fact', 'inference', 'prediction']);

    expect(badges[0]).toHaveTextContent('FACT');
    expect(badges[1]).toHaveTextContent('INFERENCE');
    expect(badges[2]).toHaveTextContent('PREDICTION');
  });

  it('renders evidence chips with file path + line range and fires onEvidenceClick', async () => {
    const onEvidenceClick = vi.fn();
    const user = userEvent.setup();
    render(<AnswerRenderer answer={SAMPLE} onEvidenceClick={onEvidenceClick} />);

    const chips = screen.getAllByTestId('evidence-chip');
    expect(chips).toHaveLength(3);
    // range with start + end
    expect(chips[0]).toHaveTextContent('src/auth/service.py:10-42');
    // range with only a start line
    expect(chips[1]).toHaveTextContent('src/auth/session.py:5');
    // no line info at all
    expect(chips[2]).toHaveTextContent('src/api/routes.py');

    await user.click(chips[0]);
    expect(onEvidenceClick).toHaveBeenCalledTimes(1);
    expect(onEvidenceClick).toHaveBeenCalledWith(
      expect.objectContaining({ file_path: 'src/auth/service.py', line_start: 10, line_end: 42 })
    );
  });

  it('renders the confidence/coverage banner', () => {
    render(<AnswerRenderer answer={SAMPLE} />);

    const banner = screen.getByTestId('confidence-banner');
    expect(banner).toHaveTextContent('82%');
    expect(screen.getByTestId('coverage-note')).toHaveTextContent(
      'Analyzed 48 of 50 files; 2 files skipped.'
    );
  });

  it('renders next-action buttons and fires onNextAction', async () => {
    const onNextAction = vi.fn();
    const user = userEvent.setup();
    render(<AnswerRenderer answer={SAMPLE} onNextAction={onNextAction} />);

    const actions = within(screen.getByTestId('next-actions')).getAllByTestId('next-action');
    expect(actions).toHaveLength(2);
    expect(actions[0]).toHaveTextContent('Open auth service');

    await user.click(actions[0]);
    expect(onNextAction).toHaveBeenCalledTimes(1);
    expect(onNextAction).toHaveBeenCalledWith(
      expect.objectContaining({ kind: 'open_file', target: 'src/auth/service.py' })
    );
  });

  it('omits the coverage note when there is none', () => {
    const noCoverage: CortexAnswer = { ...SAMPLE, coverage_note: null };
    render(<AnswerRenderer answer={noCoverage} />);
    expect(screen.queryByTestId('coverage-note')).toBeNull();
  });
});
