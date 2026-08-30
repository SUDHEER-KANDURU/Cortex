// =============================================================================
// AnswerView — thin wrapper that renders a CortexAnswer through the shared
// AnswerRenderer and wires evidence-chip clicks to the Code Navigator via the
// existing navigate event bus. Evidence chips carrying a node_id emit a
// navigate event; Task 14 refines file/line navigation. Views that already
// hold a CortexAnswer render through this component so presentation is uniform
// (Req 4.4, Req 8.2, Req 8.3).
// =============================================================================

'use client';

import React from 'react';
import { AnswerRenderer } from '@/components/answer';
import type { CortexAnswer, Evidence, NextAction } from '@/types';
import { emitNavigate } from '@/lib/navigate-events';

export interface AnswerViewProps {
  answer: CortexAnswer;
  onEvidenceClick?: (evidence: Evidence) => void;
  onNextAction?: (action: NextAction) => void;
  className?: string;
}

export default function AnswerView({
  answer,
  onEvidenceClick,
  onNextAction,
  className,
}: AnswerViewProps) {
  const handleEvidenceClick = React.useCallback(
    (evidence: Evidence) => {
      if (onEvidenceClick) {
        onEvidenceClick(evidence);
        return;
      }
      // Default behavior (Req 7.5): ask the Code Navigator to open the
      // referenced file and highlight the referenced line range. The event
      // carries file_path + line range so navigation lands on the exact code,
      // resolving by file_path first and falling back to node_id. Emit when we
      // have either a resolvable node or a file path to open.
      if (evidence.node_id || evidence.file_path) {
        emitNavigate({
          nodeId: evidence.node_id ?? '',
          label: evidence.file_path,
          nodeType: 'File',
          filePath: evidence.file_path,
          lineStart: evidence.line_start,
          lineEnd: evidence.line_end,
        });
      }
    },
    [onEvidenceClick]
  );

  return (
    <AnswerRenderer
      answer={answer}
      onEvidenceClick={handleEvidenceClick}
      onNextAction={onNextAction}
      className={className}
    />
  );
}
