// =============================================================================
// Chat Feature Types
// =============================================================================

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  isStreaming?: boolean;
}

export interface SuggestedQuestion {
  text: string;
  category: 'architecture' | 'navigation' | 'debugging' | 'understanding';
}

export const DEFAULT_SUGGESTIONS: SuggestedQuestion[] = [
  { text: 'What is the overall architecture of this repository?', category: 'architecture' },
  { text: 'Where does execution start? What are the entry points?', category: 'navigation' },
  { text: 'What are the most complex parts of the codebase?', category: 'debugging' },
  { text: 'What modules are most coupled and why?', category: 'architecture' },
  { text: 'What should I learn first to understand this codebase?', category: 'understanding' },
  { text: 'Are there any circular dependencies?', category: 'debugging' },
];
