// =============================================================================
// useChat — Streaming chat hook for Cortex AI chat
// =============================================================================

'use client';

import { useCallback, useRef, useState } from 'react';
import { streamChat, getChatHistory } from '@/lib/api/chat.api';
import type { ChatMessage } from '../chat.types';

interface UseChatOptions {
  jobId: string;
}

interface UseChatReturn {
  messages: ChatMessage[];
  isStreaming: boolean;
  error: string | null;
  sendMessage: (text: string) => void;
  stopGeneration: () => void;
  regenerate: () => void;
  clearError: () => void;
  loadHistory: () => Promise<void>;
}

let messageCounter = 0;
function nextId(): string {
  return `msg_${Date.now()}_${++messageCounter}`;
}

export function useChat({ jobId }: UseChatOptions): UseChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const sessionIdRef = useRef<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const lastUserMsgRef = useRef<string>('');

  const sendMessage = useCallback(
    (text: string) => {
      if (!text.trim() || isStreaming) return;

      lastUserMsgRef.current = text;
      setError(null);

      // Add user message
      const userMsg: ChatMessage = {
        id: nextId(),
        role: 'user',
        content: text,
        timestamp: new Date(),
      };

      // Add placeholder assistant message
      const assistantMsg: ChatMessage = {
        id: nextId(),
        role: 'assistant',
        content: '',
        timestamp: new Date(),
        isStreaming: true,
      };

      setMessages((prev) => [...prev, userMsg, assistantMsg]);
      setIsStreaming(true);

      const assistantId = assistantMsg.id;

      abortRef.current = streamChat(jobId, text, sessionIdRef.current, {
        onSessionId: (id) => {
          sessionIdRef.current = id;
        },
        onChunk: (chunk) => {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? { ...m, content: m.content + chunk }
                : m
            )
          );
        },
        onDone: () => {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId ? { ...m, isStreaming: false } : m
            )
          );
          setIsStreaming(false);
          abortRef.current = null;
        },
        onError: (errMsg) => {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantId
                ? { ...m, content: m.content || 'An error occurred.', isStreaming: false }
                : m
            )
          );
          setError(errMsg);
          setIsStreaming(false);
          abortRef.current = null;
        },
      });
    },
    [jobId, isStreaming]
  );

  const stopGeneration = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    setMessages((prev) =>
      prev.map((m) => (m.isStreaming ? { ...m, isStreaming: false } : m))
    );
    setIsStreaming(false);
  }, []);

  const regenerate = useCallback(() => {
    if (isStreaming || !lastUserMsgRef.current) return;
    // Remove the last assistant message
    setMessages((prev) => {
      const lastAssistantIdx = prev.findLastIndex((m) => m.role === 'assistant');
      if (lastAssistantIdx >= 0) {
        return prev.slice(0, lastAssistantIdx);
      }
      return prev;
    });
    // Re-send the last user message
    setTimeout(() => sendMessage(lastUserMsgRef.current), 50);
  }, [isStreaming, sendMessage]);

  const clearError = useCallback(() => setError(null), []);

  const loadHistory = useCallback(async () => {
    if (!sessionIdRef.current) return;
    try {
      const history = await getChatHistory(sessionIdRef.current);
      const loadedMessages: ChatMessage[] = history.messages.map((m) => ({
        id: nextId(),
        role: m.role,
        content: m.content,
        timestamp: new Date(m.created_at),
      }));
      setMessages(loadedMessages);
    } catch {
      // Silently fail — history loading is not critical
    }
  }, []);

  return {
    messages,
    isStreaming,
    error,
    sendMessage,
    stopGeneration,
    regenerate,
    clearError,
    loadHistory,
  };
}
