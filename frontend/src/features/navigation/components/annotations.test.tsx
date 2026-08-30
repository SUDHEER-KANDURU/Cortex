// =============================================================================
// Source annotations tests — Req 7.2
// buildAnnotations derives per-line badges from graph evidence, and SourceView
// renders them: a high-complexity function shows a complexity badge, an
// endpoint shows an endpoint marker, and a fan-in count appears.
// =============================================================================

import React from 'react';
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import SourceView from './SourceView';
import { buildAnnotations, COMPLEXITY_WARN_THRESHOLD } from './annotations';
import type { GraphNode, GraphEdge } from '@/types';

function node(
  partial: Partial<GraphNode> & Pick<GraphNode, 'id' | 'node_type'>
): GraphNode {
  return {
    label: partial.label ?? partial.id,
    job_id: 'job-1',
    properties: {},
    created_at: '',
    ...partial,
  } as GraphNode;
}

function edge(
  partial: Partial<GraphEdge> & Pick<GraphEdge, 'id' | 'source_id' | 'target_id' | 'relationship'>
): GraphEdge {
  return {
    job_id: 'job-1',
    properties: {},
    created_at: '',
    ...partial,
  } as GraphEdge;
}

const FILE = 'src/service.ts';

const FILE_NODE = node({
  id: 'f-service', node_type: 'File', label: 'service.ts', properties: { path: FILE },
});

// A high-complexity function at line 2 with two incoming callers (fan-in 2).
const COMPLEX_FN = node({
  id: 's-complex',
  node_type: 'Function',
  label: 'processOrder',
  properties: { file: FILE, line: 2, lines: 20, cyclomatic: 14 },
});

// An endpoint at line 8.
const ENDPOINT = node({
  id: 's-endpoint',
  node_type: 'Endpoint',
  label: 'GET /orders',
  properties: { file: FILE, line: 8, lines: 4, route_info: 'GET /orders' },
});

// Two callers pointing at the complex function → fan-in 2.
const EDGES: GraphEdge[] = [
  edge({ id: 'e1', source_id: 'caller-a', target_id: 's-complex', relationship: 'CALLS' }),
  edge({ id: 'e2', source_id: 'caller-b', target_id: 's-complex', relationship: 'DEPENDS_ON' }),
];

const NODES = [FILE_NODE, COMPLEX_FN, ENDPOINT];

const SOURCE = Array.from({ length: 12 }, (_, i) => `line ${i + 1}`).join('\n');

describe('buildAnnotations (Req 7.2)', () => {
  it('annotates symbol lines with complexity, fan-in, and endpoint markers', () => {
    const ann = buildAnnotations(FILE, NODES, EDGES);

    const fn = ann.get(2);
    expect(fn).toBeDefined();
    expect(fn?.complexity).toBe(14);
    expect(fn?.complexityWarn).toBe(true); // 14 >= threshold
    expect(fn?.fanIn).toBe(2);
    expect(fn?.isEndpoint).toBe(false);

    const ep = ann.get(8);
    expect(ep).toBeDefined();
    expect(ep?.isEndpoint).toBe(true);
    expect(ep?.route).toBe('GET /orders');
  });

  it('falls back to a node fan-in property when no edges are supplied', () => {
    const withProp = node({
      id: 's-prop', node_type: 'Method', label: 'm',
      properties: { file: FILE, line: 3, callers: 5 },
    });
    const ann = buildAnnotations(FILE, [FILE_NODE, withProp], []);
    expect(ann.get(3)?.fanIn).toBe(5);
  });

  it('is deterministic and only annotates symbols in the target file', () => {
    const other = node({
      id: 's-other', node_type: 'Function', label: 'unrelated',
      properties: { file: 'src/other.ts', line: 2, cyclomatic: 30 },
    });
    const a1 = buildAnnotations(FILE, [...NODES, other], EDGES);
    const a2 = buildAnnotations(FILE, [...NODES, other], EDGES);
    expect([...a1.keys()].sort()).toEqual([...a2.keys()].sort());
    // The other file's symbol must not leak into this file's annotations.
    expect(a1.get(2)?.symbolLabel).toBe('processOrder');
  });

  it('uses a threshold constant that flags high complexity', () => {
    expect(COMPLEXITY_WARN_THRESHOLD).toBeGreaterThan(0);
    const low = buildAnnotations(FILE, [
      FILE_NODE,
      node({ id: 's-low', node_type: 'Function', label: 'tiny', properties: { file: FILE, line: 1, cyclomatic: 2 } }),
    ]);
    expect(low.get(1)?.complexityWarn).toBe(false);
  });
});

describe('SourceView annotations (Req 7.2)', () => {
  it('renders complexity, endpoint, and fan-in badges on annotated lines', () => {
    const annotations = buildAnnotations(FILE, NODES, EDGES);
    render(<SourceView file={FILE_NODE} source={SOURCE} annotations={annotations} />);

    // Complexity badge on the high-complexity function line.
    const complexity = screen.getByTestId('annotation-complexity-2');
    expect(complexity).toHaveTextContent('14');

    // Fan-in badge shows the incoming reference count.
    expect(screen.getByTestId('annotation-fanin-2')).toHaveTextContent('2');

    // Endpoint marker on the endpoint line.
    const endpoint = screen.getByTestId('annotation-endpoint-8');
    expect(endpoint).toHaveTextContent('GET /orders');

    // Unannotated lines carry no annotation node.
    expect(screen.queryByTestId('source-annotation-5')).not.toBeInTheDocument();
  });

  it('renders no badges when there are no annotations', () => {
    render(<SourceView file={FILE_NODE} source={SOURCE} annotations={new Map()} />);
    expect(screen.queryByTestId('annotation-complexity-2')).not.toBeInTheDocument();
    expect(screen.queryByTestId('annotation-endpoint-8')).not.toBeInTheDocument();
  });
});
