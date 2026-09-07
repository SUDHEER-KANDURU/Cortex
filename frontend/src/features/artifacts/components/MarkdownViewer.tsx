'use client';
// =============================================================================
// MarkdownViewer — Renders markdown content with Mermaid diagram support.
// Extracts ```mermaid code blocks and renders them via MermaidDiagram.
// All other markdown is rendered with react-markdown + remark-gfm.
// =============================================================================

import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import MermaidDiagram from './MermaidDiagram';

interface MarkdownViewerProps {
  content: string;
}

export default function MarkdownViewer({ content }: MarkdownViewerProps) {
  return (
    <div className="markdown-artifact">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          // Intercept code blocks — render mermaid ones as diagrams.
          // IMPORTANT: react-markdown routes BOTH inline `code` and fenced
          // ```code``` blocks through this component. Inline code must stay
          // inline — forcing display:block on it makes every backtick-wrapped
          // word (e.g. `backend`, `routes` in a comma list) collapse onto its
          // own full-width line with large gaps. We detect fenced blocks via
          // the `language-*` class or an embedded newline; everything else is
          // treated as inline.
          code({ className, children, ...props }) {
            const match = /language-(\w+)/.exec(className || '');
            const lang = match?.[1];
            const codeString = String(children).replace(/\n$/, '');
            const isBlock = Boolean(lang) || codeString.includes('\n');

            if (lang === 'mermaid') {
              return <MermaidDiagram definition={codeString} />;
            }

            // Inline code — stays in the text flow, no block layout.
            if (!isBlock) {
              return (
                <code
                  className={className}
                  style={{
                    display: 'inline',
                    padding: '1px 6px',
                    borderRadius: 6,
                    border: '1px solid var(--border)',
                    background: 'var(--surface)',
                    fontSize: '0.9em',
                    fontFamily: 'var(--font-mono)',
                    wordBreak: 'break-word',
                    lineHeight: 'inherit',
                  }}
                  {...props}
                >
                  {children}
                </code>
              );
            }

            // Fenced code block — full-width, horizontally scrollable.
            return (
              <code
                className={className}
                style={{
                  display: 'block',
                  overflowX: 'auto',
                  whiteSpace: 'pre',
                  wordBreak: 'normal',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border)',
                  background: 'var(--surface)',
                  padding: '14px 16px',
                  fontSize: 13,
                  lineHeight: 1.75,
                  fontFamily: 'var(--font-mono)',
                  WebkitOverflowScrolling: 'touch',
                  maxWidth: '100%',
                }}
                {...props}
              >
                {codeString}
              </code>
            );
          },
          // Style headings
          h1({ children }) {
            return (
              <h1 style={{
                fontSize: 22, fontWeight: 700, letterSpacing: '-0.02em',
                color: 'var(--text)', margin: '0 0 12px',
                fontFamily: 'var(--font-display)',
                borderBottom: '1px solid var(--border)',
                paddingBottom: 10,
              }}>
                {children}
              </h1>
            );
          },
          h2({ children }) {
            return (
              <h2 style={{
                fontSize: 17, fontWeight: 700, letterSpacing: '-0.01em',
                color: 'var(--text)', margin: '28px 0 10px',
                fontFamily: 'var(--font-display)',
              }}>
                {children}
              </h2>
            );
          },
          h3({ children }) {
            return (
              <h3 style={{
                fontSize: 14, fontWeight: 700,
                color: 'var(--text)', margin: '20px 0 8px',
              }}>
                {children}
              </h3>
            );
          },
          // Style paragraphs
          p({ children }) {
            return (
              <p style={{
                fontSize: 13, lineHeight: 1.75,
                color: 'var(--text-secondary)', margin: '0 0 12px',
              }}>
                {children}
              </p>
            );
          },
          // Style blockquotes
          blockquote({ children }) {
            return (
              <blockquote style={{
                margin: '12px 0',
                padding: '12px 16px',
                borderLeft: '3px solid var(--primary)',
                background: 'var(--primary-dim)',
                borderRadius: '0 var(--radius-sm) var(--radius-sm) 0',
                fontSize: 13,
                lineHeight: 1.7,
                color: 'var(--text-secondary)',
              }}>
                {children}
              </blockquote>
            );
          },
          // Style tables — wrapped in a horizontally scrollable container so
          // wide tables (Module Summary, Key Components) scroll on their own
          // instead of squishing columns or overflowing the page on mobile.
          table({ children }) {
            return (
              <div
                className="md-table-scroll"
                style={{
                  overflowX: 'auto',
                  WebkitOverflowScrolling: 'touch',
                  margin: '12px 0',
                  borderRadius: 'var(--radius-md)',
                  border: '1px solid var(--border)',
                  maxWidth: '100%',
                }}
              >
                <table style={{
                  // min-width keeps columns readable; the wrapper scrolls
                  // horizontally rather than crushing them on narrow screens.
                  width: '100%', minWidth: 440, borderCollapse: 'collapse',
                  fontSize: 12, fontFamily: 'var(--font-mono)',
                }}>
                  {children}
                </table>
              </div>
            );
          },
          thead({ children }) {
            return (
              <thead style={{ background: 'rgba(0,0,0,0.03)' }}>
                {children}
              </thead>
            );
          },
          th({ children }) {
            return (
              <th style={{
                padding: '8px 12px', textAlign: 'left',
                fontWeight: 700, fontSize: 11,
                color: 'var(--text)', letterSpacing: '0.02em',
                borderBottom: '1px solid var(--border)',
              }}>
                {children}
              </th>
            );
          },
          td({ children }) {
            return (
              <td style={{
                padding: '7px 12px', fontSize: 12,
                color: 'var(--text-secondary)',
                borderBottom: '1px solid rgba(0,0,0,0.04)',
              }}>
                {children}
              </td>
            );
          },
          // Style lists
          ul({ children }) {
            return (
              <ul style={{
                margin: '8px 0', paddingLeft: 20,
                fontSize: 13, lineHeight: 1.75,
                color: 'var(--text-secondary)',
              }}>
                {children}
              </ul>
            );
          },
          ol({ children }) {
            return (
              <ol style={{
                margin: '8px 0', paddingLeft: 20,
                fontSize: 13, lineHeight: 1.75,
                color: 'var(--text-secondary)',
              }}>
                {children}
              </ol>
            );
          },
          li({ children }) {
            return (
              <li style={{ marginBottom: 4 }}>
                {children}
              </li>
            );
          },
          // Inline code
          // eslint-disable-next-line @typescript-eslint/no-unused-vars
          pre({ children, ...props }) {
            // Let the code component handle rendering
            return <>{children}</>;
          },
          strong({ children }) {
            return <strong style={{ color: 'var(--text)', fontWeight: 600 }}>{children}</strong>;
          },
          em({ children }) {
            return <em style={{ color: 'var(--text-secondary)', fontStyle: 'italic' }}>{children}</em>;
          },
          hr() {
            return <hr style={{ border: 'none', borderTop: '1px solid var(--border)', margin: '20px 0' }} />;
          },
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
