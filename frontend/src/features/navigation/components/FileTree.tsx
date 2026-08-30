// =============================================================================
// FileTree — Functional file tree built from graph MODULE / FILE nodes
// MODULE nodes are directories, FILE nodes are files. A nested tree is
// assembled from each node's `properties.path` (forward-slash separated).
// =============================================================================

'use client';

import React, { useMemo, useState } from 'react';
import { ChevronRight, ChevronDown, FileText, Folder, FolderOpen } from 'lucide-react';
import type { GraphNode } from '@/types';

interface FileTreeProps {
  /** All graph nodes for the job. Only MODULE and FILE nodes are used. */
  nodes: GraphNode[];
  /** The id of the currently open file node, if any. */
  selectedFileId?: string | null;
  /** Called when a FILE leaf is clicked. */
  onSelectFile: (node: GraphNode) => void;
}

// A directory or file entry in the assembled tree.
interface TreeEntry {
  name: string;
  path: string;
  /** The originating graph node (FILE for files, MODULE for dirs when present). */
  node: GraphNode | null;
  isFile: boolean;
  children: Map<string, TreeEntry>;
}

/** Read the filesystem path off a graph node's properties. */
function nodePath(node: GraphNode): string {
  const p = (node.properties.path as string) || (node.properties.file as string) || '';
  return p.replace(/\\/g, '/').replace(/^\/+/, '');
}

/**
 * Build a nested tree from MODULE (directory) and FILE nodes. FILE node paths
 * seed the full folder hierarchy; MODULE nodes attach their graph node to the
 * matching directory entry so directories are also selectable/known.
 */
function buildTree(nodes: GraphNode[]): TreeEntry {
  const root: TreeEntry = {
    name: '', path: '', node: null, isFile: false, children: new Map(),
  };

  const ensureDir = (segments: string[]): TreeEntry => {
    let cursor = root;
    let acc = '';
    for (const seg of segments) {
      if (!seg) continue;
      acc = acc ? `${acc}/${seg}` : seg;
      let next = cursor.children.get(seg);
      if (!next) {
        next = { name: seg, path: acc, node: null, isFile: false, children: new Map() };
        cursor.children.set(seg, next);
      }
      cursor = next;
    }
    return cursor;
  };

  // Files first — they create the full path skeleton.
  for (const node of nodes) {
    if (node.node_type !== 'File') continue;
    const path = nodePath(node);
    if (!path) continue;
    const segments = path.split('/');
    const fileName = segments.pop() as string;
    const dir = ensureDir(segments);
    const fileEntry: TreeEntry = {
      name: fileName, path, node, isFile: true, children: new Map(),
    };
    dir.children.set(fileName, fileEntry);
  }

  // Directories from MODULE nodes — attach the graph node to known dirs.
  for (const node of nodes) {
    if (node.node_type !== 'Module') continue;
    const path = nodePath(node);
    if (!path) continue;
    const dir = ensureDir(path.split('/'));
    if (!dir.isFile) dir.node = node;
  }

  return root;
}

/** Sort: directories before files, then alphabetical. */
function sortedChildren(entry: TreeEntry): TreeEntry[] {
  return Array.from(entry.children.values()).sort((a, b) => {
    if (a.isFile !== b.isFile) return a.isFile ? 1 : -1;
    return a.name.localeCompare(b.name);
  });
}

export default function FileTree({ nodes, selectedFileId, onSelectFile }: FileTreeProps) {
  const root = useMemo(() => buildTree(nodes), [nodes]);
  const children = sortedChildren(root);

  return (
    <div
      data-testid="file-tree"
      className="dash-scroll"
      style={{
        flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column',
        gap: 1, fontFamily: 'var(--font-mono)',
      }}
    >
      {children.length === 0 && (
        <p style={{ fontSize: 11, color: 'var(--text-muted)', padding: '8px 6px', margin: 0 }}>
          No files in graph
        </p>
      )}
      {children.map((child) => (
        <TreeNode
          key={child.path}
          entry={child}
          depth={0}
          selectedFileId={selectedFileId}
          onSelectFile={onSelectFile}
        />
      ))}
    </div>
  );
}

// ── Recursive tree row ─────────────────────────────────────────────────────────
function TreeNode({ entry, depth, selectedFileId, onSelectFile }: {
  entry: TreeEntry;
  depth: number;
  selectedFileId?: string | null;
  onSelectFile: (node: GraphNode) => void;
}) {
  const [open, setOpen] = useState(depth < 1);
  const isSelected = entry.isFile && entry.node?.id === selectedFileId;
  const indent = 6 + depth * 12;

  if (entry.isFile) {
    return (
      <button
        type="button"
        data-testid={`file-tree-file-${entry.path}`}
        onClick={() => entry.node && onSelectFile(entry.node)}
        style={{
          display: 'flex', alignItems: 'center', gap: 6,
          padding: '4px 8px', paddingLeft: indent, borderRadius: 6, width: '100%',
          cursor: 'pointer', textAlign: 'left', border: 'none',
          background: isSelected ? 'var(--primary-dim)' : 'transparent',
          transition: 'background 0.1s',
        }}
        onMouseEnter={(e) => { if (!isSelected) e.currentTarget.style.background = 'rgba(255,255,255,0.25)'; }}
        onMouseLeave={(e) => { if (!isSelected) e.currentTarget.style.background = 'transparent'; }}
      >
        <FileText style={{ width: 11, height: 11, color: 'var(--text-muted)', flexShrink: 0 }} />
        <span style={{
          fontSize: 10.5, color: 'var(--text)', overflow: 'hidden',
          textOverflow: 'ellipsis', whiteSpace: 'nowrap',
        }}>
          {entry.name}
        </span>
      </button>
    );
  }

  const kids = sortedChildren(entry);
  return (
    <>
      <button
        type="button"
        data-testid={`file-tree-dir-${entry.path}`}
        onClick={() => setOpen((v) => !v)}
        style={{
          display: 'flex', alignItems: 'center', gap: 4,
          padding: '4px 8px', paddingLeft: indent, borderRadius: 6, width: '100%',
          cursor: 'pointer', textAlign: 'left', border: 'none', background: 'transparent',
          transition: 'background 0.1s',
        }}
        onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.25)'; }}
        onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; }}
      >
        {open
          ? <ChevronDown style={{ width: 10, height: 10, color: 'var(--text-muted)', flexShrink: 0 }} />
          : <ChevronRight style={{ width: 10, height: 10, color: 'var(--text-muted)', flexShrink: 0 }} />}
        {open
          ? <FolderOpen style={{ width: 11, height: 11, color: 'var(--primary)', flexShrink: 0 }} />
          : <Folder style={{ width: 11, height: 11, color: 'var(--primary)', flexShrink: 0 }} />}
        <span style={{
          fontSize: 10.5, color: 'var(--text)', fontWeight: 600, overflow: 'hidden',
          textOverflow: 'ellipsis', whiteSpace: 'nowrap',
        }}>
          {entry.name}
        </span>
      </button>
      {open && kids.map((kid) => (
        <TreeNode
          key={kid.path}
          entry={kid}
          depth={depth + 1}
          selectedFileId={selectedFileId}
          onSelectFile={onSelectFile}
        />
      ))}
    </>
  );
}
