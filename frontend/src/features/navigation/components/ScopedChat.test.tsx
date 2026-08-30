// =============================================================================
// ScopedChat tests — Req 7.3, Req 7.6
// Binds the inline chat to {open file, selection range}:
//   • asking with a selection calls the scoped-explain client with the exact
//     file + range and renders the returned CortexAnswer,
//   • asking with no selection defaults to WHOLE-FILE scope.
// The scoped-explain client is injected (mocked) so no network is hit.
// =============================================================================

import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ScopedChat from './ScopedChat';
import type { CortexAnswer } from '@/types';

const ANSWER: CortexAnswer = {
  intent: 'scoped_explanation',
  title: 'processOrder',
  summary: 'Validates and persists an order.',
  sections: [
    {
      heading: 'Role',
      claims: [
        {
          text: 'This function orchestrates order persistence.',
          epistemic: 'inference',
          evidence: [{ file_path: 'src/service.ts', line_start: 2, line_end: 22, node_id: 's-complex' }],
        },
      ],
    },
  ],
  confidence: 0.8,
  coverage_note: null,
  next_actions: [],
};

describe('ScopedChat (Req 7.3, Req 7.6)', () => {
  it('asks scoped to the selected range and renders the returned CortexAnswer', async () => {
    const explainClient = vi.fn(async () => ANSWER);
    render(
      <ScopedChat
        jobId="job-1"
        filePath="src/service.ts"
        selection={{ lineStart: 2, lineEnd: 22 }}
        fileLineCount={120}
        explainClient={explainClient}
      />
    );

    fireEvent.change(screen.getByTestId('scoped-chat-input'), {
      target: { value: 'What does this do?' },
    });
    fireEvent.click(screen.getByTestId('scoped-chat-send'));

    await waitFor(() => {
      expect(explainClient).toHaveBeenCalledTimes(1);
    });
    expect(explainClient).toHaveBeenCalledWith('job-1', {
      file_path: 'src/service.ts',
      line_start: 2,
      line_end: 22,
      question: 'What does this do?',
    });

    // The returned answer renders through the shared AnswerView / AnswerRenderer.
    await waitFor(() => {
      expect(screen.getByTestId('answer-renderer')).toBeInTheDocument();
      expect(screen.getByTestId('answer-title')).toHaveTextContent('processOrder');
    });
  });

  it('defaults to whole-file scope when nothing is selected (Req 7.6)', async () => {
    const explainClient = vi.fn(async () => ANSWER);
    render(
      <ScopedChat
        jobId="job-1"
        filePath="src/service.ts"
        selection={null}
        fileLineCount={120}
        explainClient={explainClient}
      />
    );

    expect(screen.getByTestId('scoped-chat')).toHaveAttribute('data-scope', 'whole-file');

    fireEvent.change(screen.getByTestId('scoped-chat-input'), {
      target: { value: 'Explain this file' },
    });
    fireEvent.click(screen.getByTestId('scoped-chat-send'));

    await waitFor(() => {
      expect(explainClient).toHaveBeenCalledTimes(1);
    });
    // Whole-file scope spans line 1 .. the file's line count.
    expect(explainClient).toHaveBeenCalledWith('job-1', {
      file_path: 'src/service.ts',
      line_start: 1,
      line_end: 120,
      question: 'Explain this file',
    });
  });

  it('does not call the client when no file is open', () => {
    const explainClient = vi.fn(async () => ANSWER);
    render(
      <ScopedChat
        jobId="job-1"
        filePath={null}
        selection={null}
        fileLineCount={0}
        explainClient={explainClient}
      />
    );
    // Send is disabled with no open file.
    expect(screen.getByTestId('scoped-chat-send')).toBeDisabled();
    fireEvent.click(screen.getByTestId('scoped-chat-send'));
    expect(explainClient).not.toHaveBeenCalled();
  });
});
