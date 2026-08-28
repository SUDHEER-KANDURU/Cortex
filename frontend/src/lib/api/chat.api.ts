// =============================================================================
// Chat API — SSE streaming + session management
// =============================================================================

import { apiClient } from './client';
import { getAccessToken } from '../auth/token-storage';

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000';

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
}

export interface ChatSessionResponse {
  session_id: string;
  job_id: string;
}

export interface ChatHistoryResponse {
  session_id: string;
  job_id: string;
  messages: ChatMessage[];
}

/** Create a new chat session for a job */
export async function createSession(jobId: string): Promise<ChatSessionResponse> {
  const { data } = await apiClient.post<ChatSessionResponse>(
    '/chat/session',
    null,
    { params: { job_id: jobId } }
  );
  return data;
}

/** Get chat history for an existing session */
export async function getChatHistory(sessionId: string): Promise<ChatHistoryResponse> {
  const { data } = await apiClient.get<ChatHistoryResponse>(
    `/chat/session/${sessionId}/history`
  );
  return data;
}

/** Stream a chat response via SSE. Returns an AbortController for cancellation. */
export function streamChat(
  jobId: string,
  message: string,
  sessionId: string | null,
  callbacks: {
    onSessionId: (id: string) => void;
    onChunk: (text: string) => void;
    onDone: () => void;
    onError: (error: string) => void;
  }
): AbortController {
  const controller = new AbortController();

  const body = JSON.stringify({
    job_id: jobId,
    message,
    session_id: sessionId,
  });

  // The stream endpoint requires auth, but EventSource/fetch here bypasses
  // the axios auth interceptor — so attach the bearer token manually.
  const token = getAccessToken();
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }

  fetch(`${BASE_URL}/api/v1/chat/stream`, {
    method: 'POST',
    headers,
    body,
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        const err = await response.text();
        callbacks.onError(`Server error: ${response.status} — ${err}`);
        return;
      }

      const reader = response.body?.getReader();
      if (!reader) {
        callbacks.onError('No response stream available');
        return;
      }

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() ?? '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          const jsonStr = line.slice(6).trim();
          if (!jsonStr) continue;

          try {
            const event = JSON.parse(jsonStr);
            switch (event.type) {
              case 'session':
                callbacks.onSessionId(event.session_id);
                break;
              case 'chunk':
                callbacks.onChunk(event.text);
                break;
              case 'done':
                callbacks.onDone();
                break;
              case 'error':
                callbacks.onError(event.message);
                break;
            }
          } catch {
            // Skip malformed JSON chunks
          }
        }
      }

      // Process remaining buffer
      if (buffer.startsWith('data: ')) {
        try {
          const event = JSON.parse(buffer.slice(6).trim());
          if (event.type === 'done') callbacks.onDone();
        } catch {
          // ignore
        }
      }
    })
    .catch((err) => {
      if (err.name !== 'AbortError') {
        callbacks.onError(err.message ?? 'Connection failed');
      }
    });

  return controller;
}
