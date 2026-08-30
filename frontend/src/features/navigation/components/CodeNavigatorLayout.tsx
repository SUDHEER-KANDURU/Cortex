// =============================================================================
// CodeNavigatorLayout — Req 7.1
// Composes the Code Navigator VIEW from three regions:
//   • Left   — functional file tree built from graph MODULE / FILE nodes
//   • Center — source view of the open file
//   • Right  — inline chat panel (reused from the chat feature)
//
// Task 12 built LAYOUT + tree population. Task 13 adds:
//   • source annotations from graph evidence (complexity / fan-in / endpoint)
//   • selection-driven inline chat (ScopedChat) routing questions through the
//     scoped-explain endpoint, defaulting to whole-file scope when nothing is
//     selected (Req 7.2, Req 7.3, Req 7.6)
// Task 14 adds evidence-link navigation (Req 7.5, Req 8.3): the layout listens
// for navigate events emitted by evidence chips in any CortexAnswer and, when
// one arrives, resolves the referenced FILE node (by file_path first, else via
// node_id → node → its containing file), opens it, and highlights the
// referenced line so navigation state (open file + selection/highlight) stays
// coherent across views.
// =============================================================================

'use client';

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { FolderTree } from 'lucide-react';
import { getNavigateContext } from '@/lib/api/navigate.api';
import { onNavigateEvent, type NavigateEvent } from '@/lib/navigate-events';
import { useIsCompact } from '@/lib/utils/useBreakpoint';
import type { GraphNode, GraphEdge } from '@/types';
import FileTree from './FileTree';
import SourceView, { type SourceSelection } from './SourceView';
import ScopedChat, { type ScopedExplainClient } from './ScopedChat';
import { buildAnnotations } from './annotations';

/** Fetch source for a file node. Injectable so tests avoid the network. */
export type SourceFetcher = (jobId: string, node: GraphNode) => Promise<string>;

const defaultSourceFetcher: SourceFetcher = async (jobId, node) => {
  const ctx = await getNavigateContext(jobId, node.id);
  return ctx.source_snippet ?? '';
};

interface CodeNavigatorLayoutProps {
  jobId: string;
  nodes: GraphNode[];
  /** Graph edges — used to derive symbol fan-in for source annotations (Req 7.2). */
  edges?: GraphEdge[];
  repoName?: string;
  /** Override for source retrieval (tests / alternate transports). */
  sourceFetcher?: SourceFetcher;
  /** Override the scoped-explain client (tests / alternate transports). */
  explainClient?: ScopedExplainClient;
}

/** Read the filesystem path off a graph node's properties. */
function nodePath(node: GraphNode): string {
  const p = (node.properties.path as string) || (node.properties.file as string) || node.label;
  return (p || '').replace(/\\/g, '/').replace(/^\/+/, '');
}

/** Normalize an incoming path so it compares equal to a node's normalized path. */
function normalizePath(p: string): string {
  return (p || '').replace(/\\/g, '/').replace(/^\/+/, '');
}

/**
 * Resolve the FILE node a navigate event refers to (Req 7.5). Resolution order:
 *   1. Match a FILE node whose path equals the event's file_path.
 *   2. Fall back to the node the event's nodeId points at; if that node is a
 *      file, use it directly, otherwise map it to the FILE node sharing its
 *      path (a symbol resolves to its containing file).
 */
function resolveTargetFile(
  event: Pick<NavigateEvent, 'filePath' | 'nodeId'>,
  nodes: GraphNode[]
): GraphNode | null {
  const wantedPath = event.filePath ? normalizePath(event.filePath) : null;
  if (wantedPath) {
    const byPath = nodes.find(
      (n) => n.node_type === 'File' && nodePath(n) === wantedPath
    );
    if (byPath) return byPath;
  }

  if (event.nodeId) {
    const byId = nodes.find((n) => n.id === event.nodeId);
    if (byId) {
      if (byId.node_type === 'File') return byId;
      // Symbol node — resolve to the FILE node sharing its path.
      const symbolPath = nodePath(byId);
      const containingFile = nodes.find(
        (n) => n.node_type === 'File' && nodePath(n) === symbolPath
      );
      if (containingFile) return containingFile;
    }
  }

  return null;
}

export default function CodeNavigatorLayout({
  jobId, nodes, edges = [], sourceFetcher = defaultSourceFetcher, explainClient,
}: CodeNavigatorLayoutProps) {
  const isCompact = useIsCompact();
  const [openFile, setOpenFile] = useState<GraphNode | null>(null);
  const [source, setSource] = useState<string>('');
  const [isLoadingSource, setIsLoadingSource] = useState(false);
  // Selection range drives the scoped chat (Req 7.3); null → whole-file scope.
  const [selection, setSelection] = useState<SourceSelection | null>(null);
  // Line to visually mark + scroll to when arriving via an evidence link
  // (Req 7.5). 1-indexed; null → nothing highlighted.
  const [highlightLine, setHighlightLine] = useState<number | null>(null);

  const openFilePath = openFile ? nodePath(openFile) : null;

  // Symbol annotations for the open file, derived from graph evidence (Req 7.2).
  const annotations = useMemo(
    () => (openFilePath ? buildAnnotations(openFilePath, nodes, edges) : new Map()),
    [openFilePath, nodes, edges]
  );

  // Whole-file end bound for the default (no-selection) chat scope (Req 7.6).
  const fileLineCount = source ? source.split('\n').length : 0;

  // Open a file node, optionally highlighting a line (evidence navigation).
  // Passing highlight keeps navigation state coherent: the open file and the
  // marked line reflect the source that triggered the open (Req 7.5, Req 8.3).
  const openFileNode = useCallback(async (node: GraphNode, highlight: number | null = null) => {
    setOpenFile(node);
    setSelection(null);
    setHighlightLine(highlight);
    setSource('');
    setIsLoadingSource(true);
    try {
      const text = await sourceFetcher(jobId, node);
      setSource(text);
    } catch {
      setSource('');
    } finally {
      setIsLoadingSource(false);
    }
  }, [jobId, sourceFetcher]);

  // A manual file pick clears any evidence-driven highlight.
  const handleSelectFile = useCallback(
    (node: GraphNode) => openFileNode(node, null),
    [openFileNode]
  );

  // Task 13 seam: a selection scopes the inline chat to a line range and
  // supersedes any evidence highlight.
  const handleSelectRange = useCallback((range: SourceSelection) => {
    setSelection(range);
    setHighlightLine(null);
  }, []);

  // Evidence-link navigation (Req 7.5, Req 8.3): subscribe to navigate events
  // emitted by evidence chips in any CortexAnswer. When one carries a source
  // location, resolve the target FILE node, open it, and highlight the
  // referenced line so state stays coherent across views.
  useEffect(() => {
    const unsubscribe = onNavigateEvent((event) => {
      if (!event.filePath && !event.nodeId) return;
      const target = resolveTargetFile(event, nodes);
      if (!target) return;
      const line = event.lineStart ?? null;
      void openFileNode(target, line);
    });
    return unsubscribe;
  }, [nodes, openFileNode]);

  return (
    <div
      data-testid="code-navigator-layout"
      style={{
        display: 'flex',
        flexDirection: isCompact ? 'column' : 'row',
        gap: 14,
        minHeight: isCompact ? 0 : 460,
      }}
    >
      {/* Left — file tree */}
      <div
        data-testid="navigator-tree-region"
        style={{
          width: isCompact ? '100%' : 240,
          minWidth: isCompact ? 0 : 240,
          maxHeight: isCompact ? 240 : undefined,
          display: 'flex', flexDirection: 'column',
          padding: '10px', borderRadius: 12,
          background: 'rgba(255,255,255,0.3)', border: '0.5px solid rgba(255,255,255,0.5)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '2px 6px 10px' }}>
          <FolderTree style={{ width: 12, height: 12, color: 'var(--primary)' }} />
          <span style={{
            fontSize: 9, fontWeight: 700, letterSpacing: '0.1em', textTransform: 'uppercase',
            color: 'var(--text-muted)',
          }}>
            Files
          </span>
        </div>
        <FileTree
          nodes={nodes}
          selectedFileId={openFile?.id ?? null}
          onSelectFile={handleSelectFile}
        />
      </div>

      {/* Center — source view */}
      <div
        data-testid="navigator-source-region"
        style={{ flex: 1, minWidth: 0, minHeight: isCompact ? 240 : undefined }}
      >
        <SourceView
          file={openFile}
          source={source}
          isLoading={isLoadingSource}
          highlightLine={highlightLine}
          onSelectRange={handleSelectRange}
          annotations={annotations}
        />
      </div>

      {/* Right — inline chat panel, scoped to the open file / selection (Req 7.3, 7.6). */}
      <div
        data-testid="navigator-chat-region"
        data-scoped-file={openFilePath ?? ''}
        data-scoped-line-start={selection ? selection.lineStart : ''}
        data-scoped-line-end={selection ? selection.lineEnd : ''}
        style={{
          width: isCompact ? '100%' : 340,
          minWidth: isCompact ? 0 : 340,
          minHeight: isCompact ? 360 : undefined,
          display: 'flex', flexDirection: 'column',
        }}
      >
        <ScopedChat
          jobId={jobId}
          filePath={openFilePath}
          selection={selection}
          fileLineCount={fileLineCount}
          explainClient={explainClient}
        />
      </div>
    </div>
  );
}
