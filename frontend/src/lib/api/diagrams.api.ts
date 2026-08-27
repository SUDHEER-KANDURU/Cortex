// =============================================================================
// Diagrams API
// Fetches layered architecture diagram data from the new /diagrams endpoint.
// =============================================================================

import { apiClient } from './client';

export interface DiagramNode {
  id: string;
  label: string;
  type: 'module' | 'file' | 'class' | 'function' | 'external';
  fileCount: number;
  classCount: number;
  functionCount: number;
  lineCount: number;
  health: 'healthy' | 'warning' | 'critical';
  healthReason: string;
  inCycle: boolean;
  properties: Record<string, unknown>;
}

export interface DiagramEdge {
  id: string;
  source: string;
  target: string;
  label: string;
  type: 'imports' | 'inherits' | 'calls' | 'contains';
  weight: number;
  isCycle: boolean;
}

export interface BreadcrumbItem {
  label: string;
  level: string;
  module?: string;
  class?: string;
}

export interface DrilldownTarget {
  id: string;
  label: string;
  type: string;
}

export interface DiagramData {
  level: 'system' | 'module' | 'class';
  title: string;
  nodes: DiagramNode[];
  edges: DiagramEdge[];
  cycles: string[][];
  breadcrumb: BreadcrumbItem[];
  drilldownTargets: DrilldownTarget[];
}

/**
 * Fetch diagram data at system level (default).
 */
export async function getDiagramSystem(jobId: string): Promise<DiagramData> {
  const response = await apiClient.get<DiagramData>(`/diagrams/${jobId}?level=system`);
  return response.data;
}

/**
 * Fetch diagram data at module level.
 */
export async function getDiagramModule(jobId: string, moduleName: string): Promise<DiagramData> {
  const response = await apiClient.get<DiagramData>(
    `/diagrams/${jobId}?level=module&module=${encodeURIComponent(moduleName)}`
  );
  return response.data;
}

/**
 * Fetch diagram data at class level.
 */
export async function getDiagramClass(jobId: string, className: string): Promise<DiagramData> {
  const response = await apiClient.get<DiagramData>(
    `/diagrams/${jobId}?level=class&class=${encodeURIComponent(className)}`
  );
  return response.data;
}
