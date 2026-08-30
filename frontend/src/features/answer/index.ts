// =============================================================================
// Answer Feature — public exports
// The shared CortexAnswer presentation layer: the AnswerView wrapper (wires
// navigation) and the adapters that build a CortexAnswer from existing view
// data until dedicated backend answer endpoints land.
// =============================================================================

export { default as AnswerView } from './components/AnswerView';
export type { AnswerViewProps } from './components/AnswerView';
export { overviewToAnswer, artifactToAnswer } from './adapters';
