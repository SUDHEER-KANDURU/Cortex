// =============================================================================
// JobCard Tests
// =============================================================================

import React from 'react';
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import JobCard from './JobCard';
import type { Job } from '@/types';

const mockJob: Job = {
  id: 'abc-123',
  status: 'completed',
  artifact_type: 'architecture_diagram',
  repo_url: 'https://github.com/cortex-ai/cortex',
  created_at: '2024-06-01T10:00:00Z',
  updated_at: '2024-06-01T10:05:00Z',
};

describe('JobCard', () => {
  it('renders without crashing', () => {
    render(<JobCard job={mockJob} />);
    expect(screen.getByRole('button')).toBeDefined();
  });

  it('renders the repo URL (short form without https://github.com/ prefix)', () => {
    render(<JobCard job={mockJob} />);
    expect(screen.getByText('cortex-ai/cortex')).toBeDefined();
  });

  it('renders the artifact type as a human-readable label', () => {
    render(<JobCard job={mockJob} />);
    expect(screen.getByText('Architecture Diagram')).toBeDefined();
  });

  it('renders the StatusBadge with the correct status', () => {
    render(<JobCard job={mockJob} />);
    const badge = screen.getByTestId('status-badge');
    expect(badge.textContent).toContain('Completed');
  });

  it('calls onClick with the job when clicked', () => {
    const onClick = vi.fn();
    render(<JobCard job={mockJob} onClick={onClick} />);
    fireEvent.click(screen.getByRole('button'));
    expect(onClick).toHaveBeenCalledWith(mockJob);
  });

  it('does not throw when onClick is not provided', () => {
    render(<JobCard job={mockJob} />);
    expect(() => fireEvent.click(screen.getByRole('button'))).not.toThrow();
  });

  it('applies selected styles when isSelected is true', () => {
    render(<JobCard job={mockJob} isSelected={true} />);
    const button = screen.getByRole('button');
    expect(button.className).toContain('violet');
  });

  it('does not apply selected styles when isSelected is false', () => {
    render(<JobCard job={mockJob} isSelected={false} />);
    const button = screen.getByRole('button');
    expect(button.className).not.toContain('violet-500/10');
  });

  it('sets aria-pressed to true when selected', () => {
    render(<JobCard job={mockJob} isSelected={true} />);
    const button = screen.getByRole('button');
    expect(button.getAttribute('aria-pressed')).toBe('true');
  });

  it('sets aria-pressed to false when not selected', () => {
    render(<JobCard job={mockJob} isSelected={false} />);
    const button = screen.getByRole('button');
    expect(button.getAttribute('aria-pressed')).toBe('false');
  });
});
