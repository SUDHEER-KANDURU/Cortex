// =============================================================================
// ChatPanel — Full AI Engineering Chat experience
// Streaming responses, markdown, code blocks, suggested questions, auto-scroll
// =============================================================================

'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  MessageSquare, Send, Square,
  AlertCircle, Sparkles, Code2, GitBranch, Bug, BookOpen,
} from 'lucide-react';
import { useChat } from '../hooks/useChat';
import { DEFAULT_SUGGESTIONS, type SuggestedQuestion } from '../chat.types';
import { MessageBubble } from './MessageBubble';

interface ChatPanelProps {
  jobId: string;
  repoName?: string;
}

export default function ChatPanel({ jobId, repoName }: ChatPanelProps) {
  const { messages, isStreaming, error, sendMessage, stopGeneration, regenerate, clearError } =
    useChat({ jobId });
  const [input, setInput] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Auto-focus input
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSend = useCallback(() => {
    if (!input.trim() || isStreaming) return;
    sendMessage(input.trim());
    setInput('');
    // Reset textarea height
    if (inputRef.current) inputRef.current.style.height = 'auto';
  }, [input, isStreaming, sendMessage]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend]
  );

  const handleSuggestionClick = useCallback(
    (question: SuggestedQuestion) => {
      sendMessage(question.text);
    },
    [sendMessage]
  );

  const handleTextareaInput = useCallback((e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setInput(e.target.value);
    // Auto-resize
    const el = e.target;
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 150) + 'px';
  }, []);

  const categoryIcon = (cat: SuggestedQuestion['category']) => {
    switch (cat) {
      case 'architecture': return <GitBranch style={{ width: 12, height: 12 }} />;
      case 'navigation': return <Code2 style={{ width: 12, height: 12 }} />;
      case 'debugging': return <Bug style={{ width: 12, height: 12 }} />;
      case 'understanding': return <BookOpen style={{ width: 12, height: 12 }} />;
    }
  };

  const isEmpty = messages.length === 0;

  return (
    <div style={{
      display: 'flex', flexDirection: 'column', height: '100%',
      borderRadius: 16, overflow: 'hidden',
      background: 'rgba(255,255,255,0.45)',
      backdropFilter: 'blur(30px) saturate(170%)',
      WebkitBackdropFilter: 'blur(30px) saturate(170%)',
      border: '0.5px solid rgba(255,255,255,0.65)',
      boxShadow: '0 4px 24px rgba(80,60,20,0.06), inset 0 1px 3px rgba(255,255,255,0.6)',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 10, padding: '14px 18px',
        borderBottom: '0.5px solid rgba(255,255,255,0.5)',
        background: 'rgba(255,255,255,0.3)',
      }}>
        <div style={{
          width: 28, height: 28, borderRadius: 8,
          background: 'var(--primary-dim)', border: '0.5px solid rgba(255,255,255,0.5)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <MessageSquare style={{ width: 14, height: 14, color: 'var(--primary)' }} />
        </div>
        <div>
          <p style={{ fontSize: 13, fontWeight: 600, color: 'var(--text)', margin: 0, lineHeight: 1.2 }}>
            Cortex Chat
          </p>
          <p style={{ fontSize: 11, color: 'var(--text-muted)', margin: 0 }}>
            {repoName ? `Analyzing ${repoName}` : 'Ask about the codebase'}
          </p>
        </div>
        {isStreaming && (
          <div style={{ marginLeft: 'auto', display: 'flex', alignItems: 'center', gap: 6 }}>
            <div className="cortex-pulse" style={{
              width: 6, height: 6, borderRadius: '50%', background: 'var(--primary)',
            }} />
            <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Thinking...</span>
          </div>
        )}
      </div>

      {/* Messages area */}
      <div
        className="dash-scroll"
        style={{
          flex: 1, overflowY: 'auto', padding: '16px 18px',
          display: 'flex', flexDirection: 'column', gap: 16,
        }}
      >
        {isEmpty && (
          <div style={{
            display: 'flex', flexDirection: 'column', alignItems: 'center',
            justifyContent: 'center', flex: 1, gap: 20, padding: '40px 20px',
          }}>
            <div style={{
              width: 48, height: 48, borderRadius: 14,
              background: 'rgba(255,255,255,0.35)', border: '0.5px solid rgba(255,255,255,0.55)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <Sparkles style={{ width: 22, height: 22, color: 'var(--primary)' }} />
            </div>
            <div style={{ textAlign: 'center' }}>
              <p style={{ fontSize: 15, fontWeight: 600, color: 'var(--text)', margin: '0 0 6px' }}>
                Ask anything about this codebase
              </p>
              <p style={{ fontSize: 12, color: 'var(--text-muted)', margin: 0, maxWidth: 320 }}>
                Cortex uses the knowledge graph, engineering insights, and repository memory to ground every answer in evidence.
              </p>
            </div>

            {/* Suggested questions */}
            <div style={{
              display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 8,
              width: '100%', maxWidth: 480, marginTop: 8,
            }}>
              {DEFAULT_SUGGESTIONS.map((q) => (
                <button
                  key={q.text}
                  type="button"
                  onClick={() => handleSuggestionClick(q)}
                  style={{
                    display: 'flex', alignItems: 'flex-start', gap: 8,
                    padding: '10px 12px', borderRadius: 10, cursor: 'pointer',
                    background: 'rgba(255,255,255,0.3)', border: '0.5px solid rgba(255,255,255,0.5)',
                    textAlign: 'left', transition: 'all 0.15s ease',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.background = 'rgba(255,255,255,0.5)';
                    e.currentTarget.style.borderColor = 'rgba(255,255,255,0.7)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.background = 'rgba(255,255,255,0.3)';
                    e.currentTarget.style.borderColor = 'rgba(255,255,255,0.5)';
                  }}
                >
                  <span style={{ color: 'var(--primary)', flexShrink: 0, marginTop: 1 }}>
                    {categoryIcon(q.category)}
                  </span>
                  <span style={{ fontSize: 11, color: 'var(--text)', lineHeight: 1.4 }}>
                    {q.text}
                  </span>
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} onRegenerate={regenerate} />
        ))}

        {/* Error banner */}
        {error && (
          <div style={{
            display: 'flex', alignItems: 'center', gap: 8,
            padding: '10px 14px', borderRadius: 10,
            background: 'rgba(220,50,50,0.06)', border: '0.5px solid rgba(220,50,50,0.2)',
          }}>
            <AlertCircle style={{ width: 14, height: 14, color: 'var(--danger)', flexShrink: 0 }} />
            <p style={{ fontSize: 12, color: 'var(--danger)', margin: 0, flex: 1 }}>{error}</p>
            <button
              type="button"
              onClick={clearError}
              style={{
                background: 'none', border: 'none', cursor: 'pointer',
                fontSize: 11, color: 'var(--danger)', textDecoration: 'underline',
              }}
            >
              Dismiss
            </button>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div style={{
        padding: '12px 16px', borderTop: '0.5px solid rgba(255,255,255,0.5)',
        background: 'rgba(255,255,255,0.3)',
      }}>
        <div style={{
          display: 'flex', alignItems: 'flex-end', gap: 8,
          padding: '8px 12px', borderRadius: 12,
          background: 'rgba(255,255,255,0.5)', border: '0.5px solid rgba(255,255,255,0.6)',
        }}>
          <textarea
            ref={inputRef}
            value={input}
            onChange={handleTextareaInput}
            onKeyDown={handleKeyDown}
            placeholder="Ask about the codebase..."
            rows={1}
            style={{
              flex: 1, resize: 'none', border: 'none', outline: 'none',
              background: 'transparent', fontSize: 13, lineHeight: 1.5,
              color: 'var(--text)', fontFamily: 'var(--font-sans)',
              maxHeight: 150, minHeight: 20,
            }}
            disabled={isStreaming}
          />
          {isStreaming ? (
            <button
              type="button"
              onClick={stopGeneration}
              aria-label="Stop generation"
              style={{
                width: 32, height: 32, borderRadius: 8, cursor: 'pointer',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                background: 'var(--danger-dim)', border: '0.5px solid rgba(220,50,50,0.3)',
                color: 'var(--danger)', transition: 'all 0.15s ease', flexShrink: 0,
              }}
            >
              <Square style={{ width: 12, height: 12, fill: 'currentColor' }} />
            </button>
          ) : (
            <button
              type="button"
              onClick={handleSend}
              disabled={!input.trim()}
              aria-label="Send message"
              style={{
                width: 32, height: 32, borderRadius: 8, cursor: input.trim() ? 'pointer' : 'default',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                background: input.trim() ? 'var(--primary)' : 'rgba(255,255,255,0.3)',
                border: input.trim() ? 'none' : '0.5px solid rgba(255,255,255,0.5)',
                color: input.trim() ? '#fff' : 'var(--text-muted)',
                transition: 'all 0.15s ease', flexShrink: 0,
                opacity: input.trim() ? 1 : 0.5,
              }}
            >
              <Send style={{ width: 13, height: 13 }} />
            </button>
          )}
        </div>
        <p style={{
          fontSize: 10, color: 'var(--text-muted)', margin: '6px 0 0 4px',
          fontFamily: 'var(--font-mono)',
        }}>
          Enter to send · Shift+Enter for new line · Answers grounded in repository analysis
        </p>
      </div>
    </div>
  );
}
