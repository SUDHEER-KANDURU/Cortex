// =============================================================================
// MessageBubble — Renders a single chat message with markdown support
// Code blocks with copy button, inline code, links, lists
// =============================================================================

'use client';

import React, { useCallback, useState } from 'react';
import { Copy, Check, RefreshCw, User, Sparkles } from 'lucide-react';
import type { ChatMessage } from '../chat.types';

interface MessageBubbleProps {
  message: ChatMessage;
  onRegenerate?: () => void;
}

/** Simple markdown-to-JSX renderer (no external dependency) */
function renderMarkdown(content: string): React.ReactNode[] {
  const elements: React.ReactNode[] = [];
  const lines = content.split('\n');
  let inCodeBlock = false;
  let codeLanguage = '';
  let codeLines: string[] = [];
  let blockKey = 0;

  const flushCode = () => {
    const code = codeLines.join('\n');
    elements.push(
      <CodeBlock key={`code-${blockKey++}`} code={code} language={codeLanguage} />
    );
    codeLines = [];
    codeLanguage = '';
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Code block fences
    if (line.startsWith('```')) {
      if (inCodeBlock) {
        flushCode();
        inCodeBlock = false;
      } else {
        inCodeBlock = true;
        codeLanguage = line.slice(3).trim();
      }
      continue;
    }

    if (inCodeBlock) {
      codeLines.push(line);
      continue;
    }

    // Headers
    if (line.startsWith('### ')) {
      elements.push(
        <p key={`h3-${i}`} style={{ fontSize: 13, fontWeight: 700, margin: '12px 0 4px', color: 'var(--text)' }}>
          {renderInline(line.slice(4))}
        </p>
      );
      continue;
    }
    if (line.startsWith('## ')) {
      elements.push(
        <p key={`h2-${i}`} style={{ fontSize: 14, fontWeight: 700, margin: '14px 0 6px', color: 'var(--text)' }}>
          {renderInline(line.slice(3))}
        </p>
      );
      continue;
    }
    if (line.startsWith('# ')) {
      elements.push(
        <p key={`h1-${i}`} style={{ fontSize: 15, fontWeight: 700, margin: '16px 0 8px', color: 'var(--text)' }}>
          {renderInline(line.slice(2))}
        </p>
      );
      continue;
    }

    // List items
    if (line.match(/^[-*]\s/)) {
      elements.push(
        <div key={`li-${i}`} style={{ display: 'flex', gap: 6, margin: '2px 0', paddingLeft: 4 }}>
          <span style={{ color: 'var(--primary)', fontSize: 12, lineHeight: '1.6' }}>•</span>
          <span style={{ fontSize: 12.5, color: 'var(--text)', lineHeight: 1.6 }}>
            {renderInline(line.replace(/^[-*]\s/, ''))}
          </span>
        </div>
      );
      continue;
    }

    // Numbered list
    if (line.match(/^\d+\.\s/)) {
      const num = line.match(/^(\d+)\./)?.[1];
      elements.push(
        <div key={`ol-${i}`} style={{ display: 'flex', gap: 6, margin: '2px 0', paddingLeft: 4 }}>
          <span style={{ color: 'var(--primary)', fontSize: 12, lineHeight: '1.6', fontWeight: 600, minWidth: 14 }}>{num}.</span>
          <span style={{ fontSize: 12.5, color: 'var(--text)', lineHeight: 1.6 }}>
            {renderInline(line.replace(/^\d+\.\s/, ''))}
          </span>
        </div>
      );
      continue;
    }

    // Empty line
    if (!line.trim()) {
      elements.push(<div key={`br-${i}`} style={{ height: 8 }} />);
      continue;
    }

    // Regular paragraph
    elements.push(
      <p key={`p-${i}`} style={{ fontSize: 12.5, color: 'var(--text)', margin: '2px 0', lineHeight: 1.65 }}>
        {renderInline(line)}
      </p>
    );
  }

  // Flush any remaining code block
  if (inCodeBlock && codeLines.length > 0) {
    flushCode();
  }

  return elements;
}

/** Render inline markdown (bold, italic, code, links) */
function renderInline(text: string): React.ReactNode {
  const parts: React.ReactNode[] = [];
  let remaining = text;
  let key = 0;

  while (remaining.length > 0) {
    // Bold
    const boldMatch = remaining.match(/\*\*(.+?)\*\*/);
    // Inline code
    const codeMatch = remaining.match(/`([^`]+)`/);
    // Link
    const linkMatch = remaining.match(/\[([^\]]+)\]\(([^)]+)\)/);

    // Find earliest match
    const matches = [
      boldMatch ? { type: 'bold', index: boldMatch.index!, match: boldMatch } : null,
      codeMatch ? { type: 'code', index: codeMatch.index!, match: codeMatch } : null,
      linkMatch ? { type: 'link', index: linkMatch.index!, match: linkMatch } : null,
    ].filter(Boolean).sort((a, b) => a!.index - b!.index);

    if (matches.length === 0) {
      parts.push(remaining);
      break;
    }

    const first = matches[0]!;
    // Text before the match
    if (first.index > 0) {
      parts.push(remaining.slice(0, first.index));
    }

    switch (first.type) {
      case 'bold':
        parts.push(
          <strong key={`b-${key++}`} style={{ fontWeight: 600 }}>
            {first.match[1]}
          </strong>
        );
        remaining = remaining.slice(first.index + first.match[0].length);
        break;
      case 'code':
        parts.push(
          <code
            key={`ic-${key++}`}
            style={{
              fontSize: '0.9em', padding: '1px 5px', borderRadius: 4,
              background: 'rgba(0,0,0,0.04)', border: '0.5px solid rgba(0,0,0,0.08)',
              fontFamily: 'ui-monospace, monospace', color: 'var(--primary)',
            }}
          >
            {first.match[1]}
          </code>
        );
        remaining = remaining.slice(first.index + first.match[0].length);
        break;
      case 'link':
        parts.push(
          <a
            key={`a-${key++}`}
            href={first.match[2]}
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: 'var(--primary)', textDecoration: 'underline' }}
          >
            {first.match[1]}
          </a>
        );
        remaining = remaining.slice(first.index + first.match[0].length);
        break;
    }
  }

  return <>{parts}</>;
}

/** Code block with copy button and syntax highlighting placeholder */
function CodeBlock({ code, language }: { code: string; language: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [code]);

  return (
    <div style={{
      margin: '8px 0', borderRadius: 10, overflow: 'hidden',
      background: '#1a1a2e', border: '0.5px solid rgba(255,255,255,0.1)',
    }}>
      {/* Header bar */}
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '6px 12px', background: 'rgba(255,255,255,0.04)',
        borderBottom: '0.5px solid rgba(255,255,255,0.06)',
      }}>
        <span style={{ fontSize: 10, color: 'rgba(255,255,255,0.4)', fontFamily: 'ui-monospace, monospace' }}>
          {language || 'code'}
        </span>
        <button
          type="button"
          onClick={handleCopy}
          style={{
            display: 'flex', alignItems: 'center', gap: 4, padding: '2px 8px',
            borderRadius: 4, border: 'none', cursor: 'pointer',
            background: copied ? 'rgba(50,200,100,0.15)' : 'rgba(255,255,255,0.06)',
            color: copied ? '#50c878' : 'rgba(255,255,255,0.5)',
            fontSize: 10, transition: 'all 0.15s ease',
          }}
        >
          {copied ? <Check style={{ width: 10, height: 10 }} /> : <Copy style={{ width: 10, height: 10 }} />}
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
      {/* Code content */}
      <pre style={{
        margin: 0, padding: '12px 14px', overflowX: 'auto',
        fontSize: 11.5, lineHeight: 1.6, color: '#e0e0e0',
        fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace',
      }}>
        <code>{code}</code>
      </pre>
    </div>
  );
}

export function MessageBubble({ message, onRegenerate }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  const [copied, setCopied] = useState(false);

  const handleCopyAll = useCallback(() => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [message.content]);

  return (
    <div style={{
      display: 'flex', gap: 10, alignItems: 'flex-start',
      flexDirection: isUser ? 'row-reverse' : 'row',
    }}>
      {/* Avatar */}
      <div style={{
        width: 26, height: 26, borderRadius: 8, flexShrink: 0,
        background: isUser ? 'var(--primary-dim)' : 'rgba(255,255,255,0.35)',
        border: `0.5px solid ${isUser ? 'rgba(255,255,255,0.4)' : 'rgba(255,255,255,0.55)'}`,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        {isUser ? (
          <User style={{ width: 12, height: 12, color: 'var(--primary)' }} />
        ) : (
          <Sparkles style={{ width: 12, height: 12, color: 'var(--text-muted)' }} />
        )}
      </div>

      {/* Content */}
      <div style={{
        maxWidth: '80%', minWidth: 0,
        padding: '10px 14px', borderRadius: 12,
        background: isUser
          ? 'var(--primary-dim)'
          : 'rgba(255,255,255,0.35)',
        border: `0.5px solid ${isUser ? 'rgba(255,255,255,0.4)' : 'rgba(255,255,255,0.55)'}`,
      }}>
        {/* Streaming cursor */}
        {message.isStreaming && !message.content && (
          <div style={{ display: 'flex', gap: 4, padding: '4px 0' }}>
            <div className="cortex-pulse" style={{ width: 4, height: 4, borderRadius: '50%', background: 'var(--text-muted)' }} />
            <div className="cortex-pulse" style={{ width: 4, height: 4, borderRadius: '50%', background: 'var(--text-muted)', animationDelay: '0.15s' }} />
            <div className="cortex-pulse" style={{ width: 4, height: 4, borderRadius: '50%', background: 'var(--text-muted)', animationDelay: '0.3s' }} />
          </div>
        )}

        {/* Message content */}
        {message.content && (
          <div>{renderMarkdown(message.content)}</div>
        )}

        {/* Streaming indicator */}
        {message.isStreaming && message.content && (
          <span className="cortex-cursor" style={{
            display: 'inline-block', width: 2, height: 14,
            background: 'var(--primary)', marginLeft: 2,
            animation: 'cortex-blink 0.8s step-end infinite',
          }} />
        )}

        {/* Actions (for assistant messages, when not streaming) */}
        {!isUser && !message.isStreaming && message.content && (
          <div style={{
            display: 'flex', gap: 4, marginTop: 8, paddingTop: 6,
            borderTop: '0.5px solid rgba(255,255,255,0.3)',
          }}>
            <button
              type="button"
              onClick={handleCopyAll}
              style={{
                display: 'flex', alignItems: 'center', gap: 4,
                padding: '3px 8px', borderRadius: 6, cursor: 'pointer',
                background: 'rgba(255,255,255,0.2)', border: '0.5px solid rgba(255,255,255,0.4)',
                fontSize: 10, color: 'var(--text-muted)', transition: 'all 0.15s ease',
              }}
              onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.4)'; }}
              onMouseLeave={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.2)'; }}
            >
              {copied ? <Check style={{ width: 10, height: 10 }} /> : <Copy style={{ width: 10, height: 10 }} />}
              {copied ? 'Copied' : 'Copy'}
            </button>
            {onRegenerate && (
              <button
                type="button"
                onClick={onRegenerate}
                style={{
                  display: 'flex', alignItems: 'center', gap: 4,
                  padding: '3px 8px', borderRadius: 6, cursor: 'pointer',
                  background: 'rgba(255,255,255,0.2)', border: '0.5px solid rgba(255,255,255,0.4)',
                  fontSize: 10, color: 'var(--text-muted)', transition: 'all 0.15s ease',
                }}
                onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.4)'; }}
                onMouseLeave={(e) => { e.currentTarget.style.background = 'rgba(255,255,255,0.2)'; }}
              >
                <RefreshCw style={{ width: 10, height: 10 }} />
                Regenerate
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
