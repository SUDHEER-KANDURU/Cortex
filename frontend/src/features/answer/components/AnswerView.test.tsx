// =============================================================================
// AnswerView tests — Req 7.5, Req 8.3 (evidence-link navigation)
// Asserts that clicking an evidence chip emits a navigate event carrying the
// referenced file_path + line range, so the Code Navigator can open+highlight
// the exact code. Also verifies the caller-provided onEvidenceClick override
// still short-circuits the default emit.
// =============================================================================

import React from 'react';
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import AnswerView from './AnswerView';
import { onNavigateEvent } from '@/lib/navigate-events';
import type { CortexAnswer, Evidence } from '@/types';

function answerWithEvidence(evidence: Evidence): CortexAnswer {
  return {
    intent: 'architecture_overview',
    title: 'Overview',
    summary: '',
    confidence: 0.9,
    coverage_note: null,
    next_actions: [],
    sections: [
      {
        heading: 'Structure',
        claims: [
          {
            text: 'The entrypoint wires the app together.',
            epistemic: 'fact',
            evidence: [evidence],
          },
        ],
      },
    ],
  };
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe('AnswerView evidence-link navigation', () => {
  it('emits a navigate event carrying file_path + line range on evidence click', () => {
    const received: Array<{ filePath?: string | null; lineStart?: number | null; lineEnd?: number | null; nodeId: string }> = [];
    const unsubscribe = onNavigateEvent((e) => received.push(e));

    const evidence: Evidence = {
      file_path: 'src/main.ts',
      line_start: 12,
      line_end: 20,
      node_id: 'f-main',
    };
    render(<AnswerView answer={answerWithEvidence(evidence)} />);

    fireEvent.click(screen.getByTestId('evidence-chip'));

    expect(received).toHaveLength(1);
    expect(received[0].filePath).toBe('src/main.ts');
    expect(received[0].lineStart).toBe(12);
    expect(received[0].lineEnd).toBe(20);
    expect(received[0].nodeId).toBe('f-main');

    unsubscribe();
  });

  it('emits an event even when evidence has only a file_path (no node_id)', () => {
    const received: Array<{ filePath?: string | null; lineStart?: number | null }> = [];
    const unsubscribe = onNavigateEvent((e) => received.push(e));

    const evidence: Evidence = {
      file_path: 'src/utils/helper.ts',
      line_start: 3,
      line_end: null,
      node_id: null,
    };
    render(<AnswerView answer={answerWithEvidence(evidence)} />);

    fireEvent.click(screen.getByTestId('evidence-chip'));

    expect(received).toHaveLength(1);
    expect(received[0].filePath).toBe('src/utils/helper.ts');
    expect(received[0].lineStart).toBe(3);

    unsubscribe();
  });

  it('prefers a caller-provided onEvidenceClick and does not emit', () => {
    const spy = vi.fn();
    const unsubscribe = onNavigateEvent(spy);
    const onEvidenceClick = vi.fn();

    const evidence: Evidence = {
      file_path: 'src/main.ts',
      line_start: 1,
      line_end: null,
      node_id: 'f-main',
    };
    render(<AnswerView answer={answerWithEvidence(evidence)} onEvidenceClick={onEvidenceClick} />);

    fireEvent.click(screen.getByTestId('evidence-chip'));

    expect(onEvidenceClick).toHaveBeenCalledTimes(1);
    expect(onEvidenceClick).toHaveBeenCalledWith(evidence);
    expect(spy).not.toHaveBeenCalled();

    unsubscribe();
  });
});
