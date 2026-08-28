// =============================================================================
// useNavigate — Hook for the Navigate feature
// Manages navigation state: current node, history, breadcrumb, mode
// =============================================================================

'use client';

import { useCallback, useRef, useState } from 'react';
import {
  getNavigateContext,
  getNavigateImpact,
  getNavigateExplain,
  type NavigateResponse,
  type ConnectedNode,
  type NavigateExplainResponse,
  type NavigationMode,
} from '@/lib/api/navigate.api';

export interface NavigateHistoryEntry {
  nodeId: string;
  label: string;
  nodeType: string;
}

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  /** Evidence the answer was grounded in (assistant messages only) */
  evidence?: string[];
  confidence?: number;
  /** True while this assistant message is still being generated */
  pending?: boolean;
  /** True if the answer failed to generate */
  error?: boolean;
}

export interface UseNavigateReturn {
  // Current state
  current: NavigateResponse | null;
  isLoading: boolean;
  error: string | null;
  mode: NavigationMode;

  // History / navigation
  history: NavigateHistoryEntry[];
  historyIndex: number;
  canGoBack: boolean;
  canGoForward: boolean;

  // Actions
  navigateTo: (nodeId: string) => Promise<void>;
  goBack: () => void;
  goForward: () => void;
  setMode: (mode: NavigationMode) => void;

  // Impact
  impact: ConnectedNode[] | null;
  isLoadingImpact: boolean;
  loadImpact: () => Promise<void>;

  // Explain
  explanation: NavigateExplainResponse | null;
  isLoadingExplain: boolean;
  loadExplanation: (question?: string) => Promise<void>;

  // Chat — conversational deep-dive scoped to the current entity
  chatMessages: ChatMessage[];
  isChatting: boolean;
  askChat: (question: string) => Promise<void>;
  clearChat: () => void;
}

export function useNavigate(jobId: string): UseNavigateReturn {
  const [current, setCurrent] = useState<NavigateResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [mode, setMode] = useState<NavigationMode>('overview');

  const [history, setHistory] = useState<NavigateHistoryEntry[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);

  const [impact, setImpact] = useState<ConnectedNode[] | null>(null);
  const [isLoadingImpact, setIsLoadingImpact] = useState(false);

  const [explanation, setExplanation] = useState<NavigateExplainResponse | null>(null);
  const [isLoadingExplain, setIsLoadingExplain] = useState(false);

  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [isChatting, setIsChatting] = useState(false);

  // Track active request to prevent race conditions
  const activeRequest = useRef(0);

  const navigateTo = useCallback(async (nodeId: string) => {
    const requestId = ++activeRequest.current;
    setIsLoading(true);
    setError(null);
    // Clear mode-specific data on navigation
    setImpact(null);
    setExplanation(null);
    setChatMessages([]);

    try {
      const data = await getNavigateContext(jobId, nodeId);
      if (requestId !== activeRequest.current) return; // stale

      setCurrent(data);

      // Update history
      setHistory(prev => {
        const newHistory = prev.slice(0, historyIndex + 1);
        newHistory.push({
          nodeId: data.id,
          label: data.label,
          nodeType: data.node_type,
        });
        return newHistory;
      });
      setHistoryIndex(prev => prev + 1);
    } catch (err: unknown) {
      if (requestId !== activeRequest.current) return;
      setError(err instanceof Error ? err.message : 'Failed to load navigation context');
    } finally {
      if (requestId === activeRequest.current) setIsLoading(false);
    }
  }, [jobId, historyIndex]);

  const goBack = useCallback(() => {
    if (historyIndex <= 0) return;
    const prevEntry = history[historyIndex - 1];
    if (!prevEntry) return;

    setHistoryIndex(prev => prev - 1);
    setIsLoading(true);
    setError(null);
    setImpact(null);
    setExplanation(null);
    setChatMessages([]);

    const requestId = ++activeRequest.current;
    getNavigateContext(jobId, prevEntry.nodeId).then(data => {
      if (requestId !== activeRequest.current) return;
      setCurrent(data);
      setIsLoading(false);
    }).catch(err => {
      if (requestId !== activeRequest.current) return;
      setError(err instanceof Error ? err.message : 'Navigation failed');
      setIsLoading(false);
    });
  }, [jobId, history, historyIndex]);

  const goForward = useCallback(() => {
    if (historyIndex >= history.length - 1) return;
    const nextEntry = history[historyIndex + 1];
    if (!nextEntry) return;

    setHistoryIndex(prev => prev + 1);
    setIsLoading(true);
    setError(null);
    setImpact(null);
    setExplanation(null);
    setChatMessages([]);

    const requestId = ++activeRequest.current;
    getNavigateContext(jobId, nextEntry.nodeId).then(data => {
      if (requestId !== activeRequest.current) return;
      setCurrent(data);
      setIsLoading(false);
    }).catch(err => {
      if (requestId !== activeRequest.current) return;
      setError(err instanceof Error ? err.message : 'Navigation failed');
      setIsLoading(false);
    });
  }, [jobId, history, historyIndex]);

  const loadImpact = useCallback(async () => {
    if (!current) return;
    setIsLoadingImpact(true);
    try {
      const data = await getNavigateImpact(jobId, current.id);
      setImpact(data);
    } catch {
      // Silent failure for impact — non-critical
    } finally {
      setIsLoadingImpact(false);
    }
  }, [jobId, current]);

  const loadExplanation = useCallback(async (question?: string) => {
    if (!current) return;
    setIsLoadingExplain(true);
    try {
      const data = await getNavigateExplain(jobId, current.id, question);
      setExplanation(data);
    } catch (err: unknown) {
      setExplanation({
        explanation: err instanceof Error ? err.message : 'Explanation unavailable',
        evidence_used: [],
        confidence: 0,
      });
    } finally {
      setIsLoadingExplain(false);
    }
  }, [jobId, current]);

  const askChat = useCallback(async (question: string) => {
    const trimmed = question.trim();
    if (!current || !trimmed || isChatting) return;

    const nodeId = current.id;
    // Append the user message + a pending assistant placeholder in one update.
    setChatMessages(prev => [
      ...prev,
      { role: 'user', content: trimmed },
      { role: 'assistant', content: '', pending: true },
    ]);
    setIsChatting(true);

    try {
      const data = await getNavigateExplain(jobId, nodeId, trimmed);
      // Guard: user may have navigated away mid-request.
      if (current?.id !== nodeId) return;
      setChatMessages(prev => {
        const next = [...prev];
        // Replace the trailing pending placeholder.
        for (let i = next.length - 1; i >= 0; i--) {
          if (next[i].role === 'assistant' && next[i].pending) {
            next[i] = {
              role: 'assistant',
              content: data.explanation || 'No answer was generated.',
              evidence: data.evidence_used,
              confidence: data.confidence,
            };
            break;
          }
        }
        return next;
      });
    } catch (err: unknown) {
      setChatMessages(prev => {
        const next = [...prev];
        for (let i = next.length - 1; i >= 0; i--) {
          if (next[i].role === 'assistant' && next[i].pending) {
            next[i] = {
              role: 'assistant',
              content:
                err instanceof Error
                  ? err.message
                  : 'Could not generate an answer. The AI service may be unavailable.',
              error: true,
            };
            break;
          }
        }
        return next;
      });
    } finally {
      setIsChatting(false);
    }
  }, [jobId, current, isChatting]);

  const clearChat = useCallback(() => {
    setChatMessages([]);
  }, []);

  return {
    current,
    isLoading,
    error,
    mode,
    history,
    historyIndex,
    canGoBack: historyIndex > 0,
    canGoForward: historyIndex < history.length - 1,
    navigateTo,
    goBack,
    goForward,
    setMode,
    impact,
    isLoadingImpact,
    loadImpact,
    explanation,
    isLoadingExplain,
    loadExplanation,
    chatMessages,
    isChatting,
    askChat,
    clearChat,
  };
}
