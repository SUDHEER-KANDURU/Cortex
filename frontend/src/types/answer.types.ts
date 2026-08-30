// =============================================================================
// CortexAnswer contract (frontend)
// Mirrors the backend domain model (spec Tasks 6-9). Every Cortex output —
// module breakdown, API spec, learning path, interview prep, architecture
// overview, scoped explanation — is serialized as a CortexAnswer and rendered
// through the single shared AnswerRenderer.
//
// The backend serializes the epistemic tag and next-action kind as their
// lowercase string enum values, so we model them as string literal unions.
// =============================================================================

/** How much Cortex trusts a claim. */
export type EpistemicTag = 'fact' | 'inference' | 'prediction';

/** What a next-action button does when clicked. */
export type NextActionKind =
  | 'open_file'
  | 'view_node'
  | 'ask_question'
  | 'run_producer';

/** A concrete reference backing a claim (file + optional line range + node). */
export interface Evidence {
  file_path: string;
  line_start: number | null;
  line_end: number | null;
  node_id: string | null;
}

/** A single statement, tagged with its epistemic status and its evidence. */
export interface Claim {
  text: string;
  epistemic: EpistemicTag;
  evidence: Evidence[];
}

/** An ordered group of claims under a heading. */
export interface AnswerSection {
  heading: string;
  claims: Claim[];
}

/** A suggested follow-up the user can trigger from an answer. */
export interface NextAction {
  label: string;
  kind: NextActionKind;
  target: string;
  line_start: number | null;
  line_end: number | null;
}

/** The single unified answer shape every feature produces. */
export interface CortexAnswer {
  intent: string;
  title: string;
  summary: string;
  sections: AnswerSection[];
  /** 0..1 */
  confidence: number;
  coverage_note: string | null;
  next_actions: NextAction[];
}
