// =============================================================================
// Artifacts Feature — Local Types
// Types specific to the artifacts feature.
// =============================================================================

import type { Artifact } from '@/types';

/** Supported content types for inline artifact rendering */
export type ArtifactContentType =
  | 'mermaid'
  | 'text/markdown'
  | 'application/json'
  | 'text/plain';

/** State for the useArtifact hook */
export interface ArtifactState {
  artifacts: Artifact[];
  isLoading: boolean;
  error: string | null;
}

/** Props for components that display a list of artifacts */
export interface ArtifactListProps {
  jobId: string;
}
