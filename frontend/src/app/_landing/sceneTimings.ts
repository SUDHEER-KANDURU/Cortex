// =============================================================================
// Scene Timings — shared timeline map for the Cortex cinematic experience
// Both CortexCube.tsx (3D) and page.tsx (DOM overlays) key off these exact
// values so the cube and the story text stay perfectly synchronized without
// needing to pass a live progress value across components on every frame.
// =============================================================================

/** Total scroll distance for the pinned cinematic stage, in viewport heights (vh). */
export const TOTAL_SCRUB_VH = 1300;

/** Named beats along the master timeline, in gsap timeline "seconds" (arbitrary unit, 0–13). */
export const SCENES = {
  idle: 0,
  ingest: 1,
  thinking: 2.2,
  separate: 3.5,
  pipeline: 5,
  reasoning: 6.5,
  artifacts: 8,
  selfAnalysis: 10,
  reassemble: 11.5,
  finale: 12.3,
  end: 13,
} as const;

export const SCROLL_TRIGGER_CONFIG = {
  start: 'top top',
  end: `+=${TOTAL_SCRUB_VH}%`,
  scrub: 1.2,
} as const;
