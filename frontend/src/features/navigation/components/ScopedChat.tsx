// =============================================================================
// ScopedChat — selection-driven inline chat for the Code Navigator
// (Req 7.3, Req 7.6)
//
// The user asks a question about the open file. The chat is bound to
// {open file, selection range}:
//   • With a selection → the question is scoped to that line range. The backend
//     resolves the range to the graph node(s) at those lines and returns a
//     Scoped Explanation as a CortexAnswer (Req 7.3).
//   • With no selection → the chat defaults to WHOLE-FILE scope: the request
//     spans the full file (line 1 .. line count), so the backend scopes the
//     answer to the currently open file (Req 7.6).
//
// The returned CortexAnswer renders through the shared AnswerView (Task 10), so
// scoped explanations look identical to every other Cortex answer.
// =============================================================================

'use client';

import React, { useCallback, useState } from 'react';
import { MessageSquare, Send, AlertTriangle } from 'lucide-react';
import { AnswerView } from '@/features/answer';
import { explainScope, type ScopedExplainRequest } from '@/lib/api/navigate.api';
import type { CortexAnswer } from '@/types';
import type { SourceSelection } from './SourceView';

/** Injectable client so tests avoid the network. Defaults to the real API. */
export type ScopedExplainClient = (
  jobId: string,
  request: ScopedExplainRequest
) => Promise<CortexAnswer>;

interface ScopedChatProps {
  jobId: string;
  /** Path of the currently open file, or null when nothing is open. */
  filePath: string | null;
  /** Current selection, or null for whole-file scope (Req 7.6). */
  selection: SourceSelection | null;
  /** Line count of the open file — used as the whole-file end bound. */
  fileLineCount: number;
  /** Override the scoped-explain client (tests / alternate transports). */
  explainClient?: ScopedExplainClient;
}

export default function ScopedChat({
  jobId, filePath, selection, fileLineCount, explainClient = explainScope,
}: ScopedChatProps) {
  const [question, setQuestion] = useState('');
  const [answer, setAnswer] = useState<CortexAnswer | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const hasFile = Boolean(filePath);

  const ask = useCallback(async () => {
    if (!filePath) return;
    const q = question.trim();

    // Bind to {open file, selection range}. When nothing is selected, default
    // to whole-file scope by spanning the full file (Req 7.6). If the line
    // count is unknown, line 1 still keeps the request valid and the backend
    // falls back to whole-file scope when no inner symbol matches.
    const lineStart = selection ? selection.lineStart : 1;
    const lineEnd = selection
      ? selection.lineEnd
      : Math.max(1, fileLineCount || 1);

    setIsLoading(true);
    setError(null);
    try {
      const result = await explainClient(jobId, {
        file_path: filePath,
        line_start: lineStart,
        line_end: lineEnd,
        question: q,
      });
      setAnswer(result);
    } catch (e) {
      setAnswer(null);
      setError(e instanceof Error ? e.message : 'Failed to explain this code.');
    } finally {
      setIsLoading(false);
    }
  }, [filePath, question, selection, fileLineCount, explainClient, jobId]);

  const onKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter' && !e.shiftKey && hasFile && !isLoading) {
        e.preventDefault();
        void ask();
      }
    },
    [ask, hasFile, isLoading]
  );

  const scopeLabel = !hasFile
    ? 'Open a file to ask about it'
    : selection
      ? `Scoped to lines ${selection.lineStart}${
          selection.lineEnd !== selection.lineStart ? `–${selection.lineEnd}` : ''
        }`
      : 'Scoped to the whole file';

  return (
    <div
      data-testid="scoped-chat"
      data-scope={selection ? 'selection' : 'whole-file'}
      style={{
        display: 'flex', flexDirection: 'column', height: '100%', minHeight: 240,
        borderRadius: 12, overflow: 'hidden',
        background: 'rgba(255,255,255,0.35)', border: '0.5px solid rgba(255,255,255,0.55)',
      }}
    >
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8, padding: '10px 14px',
        borderBottom: '0.5px solid rgba(255,255,255,0.5)', background: 'rgba(255,255,255,0.3)',
      }}>
        <MessageSquare style={{ width: 13, height: 13, color: 'var(--primary)' }} />
        <span style={{ fontSize: 11, fontWeight: 700, color: 'var(--text)' }}>Ask about this code</span>
        <span
          data-testid="scoped-chat-scope-label"
          style={{
            marginLeft: 'auto', fontSize: 9.5, color: 'var(--text-muted)',
            fontFamily: 'var(--font-mono)',
          }}
        >
          {scopeLabel}
        </span>
      </div>

      {/* Answer / status body */}
      <div className="dash-scroll" style={{ flex: 1, overflow: 'auto', padding: '12px 14px' }}>
        {isLoading && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '12px 0' }}>
            <div className="cortex-pulse" style={{ width: 6, height: 6, borderRadius: '50%', background: 'var(--primary)' }} />
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>Explaining...</span>
          </div>
        )}

        {!isLoading && error && (
          <div
            data-testid="scoped-chat-error"
            style={{
              display: 'flex', alignItems: 'flex-start', gap: 8, padding: '10px 12px',
              borderRadius: 10, background: 'rgba(249,115,22,0.08)',
              border: '0.5px solid rgba(249,115,22,0.25)',
            }}
          >
            <AlertTriangle style={{ width: 13, height: 13, color: '#f97316', flexShrink: 0, marginTop: 1 }} />
            <span style={{ fontSize: 12, color: 'var(--text)' }}>{error}</span>
          </div>
        )}

        {!isLoading && !error && answer && (
          <AnswerView answer={answer} />
        )}

        {!isLoading && !error && !answer && (
          <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: 0, lineHeight: 1.6 }}>
            {hasFile
              ? 'Select a range in the source and ask a question, or ask about the whole file.'
              : 'Open a file from the tree to ask Cortex about it.'}
          </p>
        )}
      </div>

      {/* Composer */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8, padding: '10px 12px',
        borderTop: '0.5px solid rgba(255,255,255,0.5)', background: 'rgba(255,255,255,0.3)',
      }}>
        <input
          type="text"
          data-testid="scoped-chat-input"
          value={question}
          disabled={!hasFile || isLoading}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder={hasFile ? 'Ask about this code...' : 'Open a file first'}
          style={{
            flex: 1, border: '0.5px solid rgba(255,255,255,0.5)', outline: 'none',
            background: 'rgba(255,255,255,0.4)', borderRadius: 8, padding: '7px 10px',
            fontSize: 12, color: 'var(--text)', fontFamily: 'var(--font-sans)',
          }}
        />
        <button
          type="button"
          data-testid="scoped-chat-send"
          onClick={() => void ask()}
          disabled={!hasFile || isLoading}
          style={{
            display: 'inline-flex', alignItems: 'center', gap: 5, fontSize: 12, fontWeight: 600,
            padding: '7px 12px', borderRadius: 8, border: '0.5px solid rgba(255,255,255,0.45)',
            background: 'var(--primary-dim)', color: 'var(--primary)',
            cursor: !hasFile || isLoading ? 'not-allowed' : 'pointer',
            opacity: !hasFile || isLoading ? 0.6 : 1,
          }}
        >
          <Send style={{ width: 12, height: 12 }} aria-hidden="true" />
          Ask
        </button>
      </div>
    </div>
  );
}
