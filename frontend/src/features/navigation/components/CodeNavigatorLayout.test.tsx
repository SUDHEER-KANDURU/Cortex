// =============================================================================
// CodeNavigatorLayout tests — Req 7.1, Req 8.1
// Renders the Code Navigator layout from sample graph MODULE / FILE nodes and
// asserts: the file tree renders from the nodes, the three regions (tree,
// source view, chat) are present, and selecting a file updates the source view.
// =============================================================================

import React from 'react';
import { beforeAll, describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import CodeNavigatorLayout from './CodeNavigatorLayout';
import { emitNavigate } from '@/lib/navigate-events';
import type { GraphNode } from '@/types';

// jsdom does not implement scrollIntoView; ChatPanel + evidence navigation call it.
beforeAll(() => {
  Element.prototype.scrollIntoView = vi.fn();
});

// The chat feature's useChat imports the chat API at module load; stub it so
// the test stays hermetic (no network, no SSE).
vi.mock('@/lib/api/chat.api', () => ({
  streamChat: vi.fn(() => new AbortController()),
  getChatHistory: vi.fn(async () => ({ session_id: 's', job_id: 'j', messages: [] })),
  createSession: vi.fn(async () => ({ session_id: 's', job_id: 'j' })),
}));

// Avoid the real navigate API being hit if the default fetcher / scoped chat
// client is ever used. ScopedChat imports `explainScope` from this module, so
// it must be stubbed too.
vi.mock('@/lib/api/navigate.api', () => ({
  getNavigateContext: vi.fn(async () => ({ source_snippet: '' })),
  explainScope: vi.fn(async () => ({
    intent: 'scoped_explanation',
    title: '',
    summary: '',
    sections: [],
    confidence: 0,
    coverage_note: null,
    next_actions: [],
  })),
}));

function node(partial: Partial<GraphNode> & Pick<GraphNode, 'id' | 'node_type'>): GraphNode {
  return {
    label: partial.label ?? partial.id,
    job_id: 'job-1',
    properties: {},
    ...partial,
  } as GraphNode;
}

const NODES: GraphNode[] = [
  node({ id: 'repo', node_type: 'Repository', label: 'repo' }),
  node({ id: 'm-src', node_type: 'Module', label: 'src/', properties: { path: 'src' } }),
  node({ id: 'm-src-utils', node_type: 'Module', label: 'utils/', properties: { path: 'src/utils' } }),
  node({ id: 'f-main', node_type: 'File', label: 'main.ts', properties: { path: 'src/main.ts' } }),
  node({ id: 'f-helper', node_type: 'File', label: 'helper.ts', properties: { path: 'src/utils/helper.ts' } }),
  node({ id: 'f-readme', node_type: 'File', label: 'README.md', properties: { path: 'README.md' } }),
];

describe('CodeNavigatorLayout', () => {
  it('renders the three regions: file tree, source view, and inline chat', () => {
    render(<CodeNavigatorLayout jobId="job-1" nodes={NODES} sourceFetcher={vi.fn(async () => '')} />);

    expect(screen.getByTestId('navigator-tree-region')).toBeInTheDocument();
    expect(screen.getByTestId('navigator-source-region')).toBeInTheDocument();
    expect(screen.getByTestId('navigator-chat-region')).toBeInTheDocument();
    expect(screen.getByTestId('file-tree')).toBeInTheDocument();
    expect(screen.getByTestId('source-view')).toBeInTheDocument();
  });

  it('builds the file tree from graph MODULE / FILE nodes (dirs and files appear)', () => {
    render(<CodeNavigatorLayout jobId="job-1" nodes={NODES} sourceFetcher={vi.fn(async () => '')} />);

    // Top-level directory and file from the paths.
    expect(screen.getByTestId('file-tree-dir-src')).toBeInTheDocument();
    expect(screen.getByTestId('file-tree-file-README.md')).toBeInTheDocument();

    // Directory contents (src is expanded at depth 0).
    expect(screen.getByTestId('file-tree-file-src/main.ts')).toBeInTheDocument();
    // Nested module directory appears too.
    expect(screen.getByTestId('file-tree-dir-src/utils')).toBeInTheDocument();

    // The Repository node is not rendered as a tree entry.
    expect(screen.queryByText('repo')).not.toBeInTheDocument();
  });

  it('updates the source view when a file is selected', async () => {
    const sourceFetcher = vi.fn(async () => 'const answer = 42;\nexport default answer;');
    render(<CodeNavigatorLayout jobId="job-1" nodes={NODES} sourceFetcher={sourceFetcher} />);

    // Initially no file is open.
    expect(screen.getByTestId('source-view-path')).toHaveTextContent('No file open');

    fireEvent.click(screen.getByTestId('file-tree-file-src/main.ts'));

    await waitFor(() => {
      expect(sourceFetcher).toHaveBeenCalledTimes(1);
      expect(screen.getByTestId('source-view-path')).toHaveTextContent('src/main.ts');
    });

    // The fetched source now renders in the source view region.
    await waitFor(() => {
      expect(screen.getByTestId('source-line-1')).toHaveTextContent('const answer = 42;');
    });
  });

  it('exposes the open file to the chat region as a scoping seam', async () => {
    const sourceFetcher = vi.fn(async () => 'x');
    render(<CodeNavigatorLayout jobId="job-1" nodes={NODES} sourceFetcher={sourceFetcher} />);

    fireEvent.click(screen.getByTestId('file-tree-file-src/main.ts'));

    await waitFor(() => {
      expect(screen.getByTestId('navigator-chat-region')).toHaveAttribute(
        'data-scoped-file',
        'src/main.ts',
      );
    });
  });

  // ── Evidence-link navigation (Req 7.5, Req 8.3) ────────────────────────────
  describe('evidence-link navigation', () => {
    it('opens the referenced file and highlights the referenced line on a navigate event', async () => {
      const sourceFetcher = vi.fn(async () => 'line one\nline two\nline three\nline four');
      render(<CodeNavigatorLayout jobId="job-1" nodes={NODES} sourceFetcher={sourceFetcher} />);

      // Nothing open initially.
      expect(screen.getByTestId('source-view-path')).toHaveTextContent('No file open');

      // Evidence chip in some CortexAnswer fires this via emitNavigate.
      act(() => {
        emitNavigate({
          nodeId: 'f-main',
          label: 'src/main.ts',
          nodeType: 'File',
          filePath: 'src/main.ts',
          lineStart: 3,
          lineEnd: 3,
        });
      });

      // The Navigator opened the referenced file...
      await waitFor(() => {
        expect(sourceFetcher).toHaveBeenCalledTimes(1);
        expect(screen.getByTestId('source-view-path')).toHaveTextContent('src/main.ts');
      });

      // ...and highlighted the referenced line (state stays coherent).
      await waitFor(() => {
        expect(screen.getByTestId('source-line-3')).toHaveAttribute('data-highlighted', 'true');
      });
      expect(screen.getByTestId('source-line-1')).not.toHaveAttribute('data-highlighted');
    });

    it('resolves the file by file_path when no matching node id is present', async () => {
      const sourceFetcher = vi.fn(async () => 'a\nb');
      render(<CodeNavigatorLayout jobId="job-1" nodes={NODES} sourceFetcher={sourceFetcher} />);

      act(() => {
        emitNavigate({
          nodeId: '',
          label: 'src/utils/helper.ts',
          nodeType: 'File',
          filePath: 'src/utils/helper.ts',
          lineStart: 2,
          lineEnd: null,
        });
      });

      await waitFor(() => {
        expect(screen.getByTestId('source-view-path')).toHaveTextContent('src/utils/helper.ts');
        expect(screen.getByTestId('source-line-2')).toHaveAttribute('data-highlighted', 'true');
      });
    });

    it('ignores navigate events that resolve to no known file', async () => {
      const sourceFetcher = vi.fn(async () => 'a');
      render(<CodeNavigatorLayout jobId="job-1" nodes={NODES} sourceFetcher={sourceFetcher} />);

      act(() => {
        emitNavigate({
          nodeId: 'does-not-exist',
          label: 'ghost.ts',
          nodeType: 'File',
          filePath: 'ghost.ts',
          lineStart: 1,
          lineEnd: 1,
        });
      });

      // No file opened; nothing fetched.
      expect(sourceFetcher).not.toHaveBeenCalled();
      expect(screen.getByTestId('source-view-path')).toHaveTextContent('No file open');
    });
  });
});
