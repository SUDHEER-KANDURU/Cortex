// =============================================================================
// Navigation Feature — Public exports
// =============================================================================

export { default as CodeNavigator } from './components/CodeNavigator';
export { default as CodeNavigatorLayout } from './components/CodeNavigatorLayout';
export type { SourceFetcher } from './components/CodeNavigatorLayout';
export { default as FileTree } from './components/FileTree';
export { default as SourceView } from './components/SourceView';
export type { SourceSelection } from './components/SourceView';
export { default as ScopedChat } from './components/ScopedChat';
export type { ScopedExplainClient } from './components/ScopedChat';
export { buildAnnotations, COMPLEXITY_WARN_THRESHOLD } from './components/annotations';
export type { LineAnnotation } from './components/annotations';
export { default as NavigatePanel } from './components/NavigatePanel';
export { ExplainOverlay } from './components/NavigatePanel';
export { useNavigate } from './hooks/useNavigate';
