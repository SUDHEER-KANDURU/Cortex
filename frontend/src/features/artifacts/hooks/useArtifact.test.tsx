import React from 'react';
import { act, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useArtifact } from './useArtifact';
import { getArtifactsForJob } from '@/lib/api/artifacts.api';

vi.mock('@/lib/api/artifacts.api', () => ({
  getArtifactsForJob: vi.fn(),
}));

function HookProbe({ jobId }: { jobId: string | null }) {
  const { refetch } = useArtifact(jobId);
  const firstRef = React.useRef<(() => void) | null>(null);

  if (firstRef.current === null) {
    firstRef.current = refetch;
  }

  return <div data-testid="stable">{firstRef.current === refetch ? 'stable' : 'changed'}</div>;
}

describe('useArtifact', () => {
  beforeEach(() => {
    vi.mocked(getArtifactsForJob).mockResolvedValue([]);
  });

  it('keeps the refetch callback stable across rerenders', () => {
    const { rerender } = render(<HookProbe jobId="job-1" />);

    act(() => {
      rerender(<HookProbe jobId="job-1" />);
    });

    expect(screen.getByTestId('stable').textContent).toBe('stable');
  });
});
