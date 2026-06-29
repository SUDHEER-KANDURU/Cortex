// =============================================================================
// JobSubmitForm Tests
// =============================================================================

import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import JobSubmitForm from './JobSubmitForm';

// Mock the useSubmitJob hook to avoid real API calls
vi.mock('@/features/jobs/hooks/useSubmitJob', () => ({
  useSubmitJob: vi.fn(),
}));

import { useSubmitJob } from '@/features/jobs/hooks/useSubmitJob';
import type { Job } from '@/types';

const mockJob: Job = {
  id: 'test-uuid-1234',
  status: 'pending',
  artifact_type: 'architecture_diagram',
  repo_url: 'https://github.com/owner/repo',
  created_at: '2024-06-01T12:00:00Z',
  updated_at: '2024-06-01T12:00:00Z',
};

function makeMockHook(overrides = {}) {
  return {
    submittedJob: null,
    isSubmitting: false,
    error: null,
    submitJob: vi.fn().mockResolvedValue(undefined),
    ...overrides,
  };
}

describe('JobSubmitForm', () => {
  beforeEach(() => {
    vi.mocked(useSubmitJob).mockReturnValue(makeMockHook());
  });

  it('renders without crashing', () => {
    render(<JobSubmitForm onJobSubmitted={vi.fn()} />);
    expect(screen.getByLabelText(/GitHub Repository URL/i)).toBeDefined();
    expect(screen.getByLabelText(/Artifact Type/i)).toBeDefined();
    expect(screen.getByRole('button', { name: /Analyze Repository/i })).toBeDefined();
  });

  it('submit button is disabled when the URL field is empty', () => {
    render(<JobSubmitForm onJobSubmitted={vi.fn()} />);
    const button = screen.getByRole('button', { name: /Analyze Repository/i });
    expect((button as HTMLButtonElement).disabled).toBe(true);
  });

  it('submit button is enabled when a URL is entered', async () => {
    render(<JobSubmitForm onJobSubmitted={vi.fn()} />);
    const input = screen.getByLabelText(/GitHub Repository URL/i);
    await userEvent.type(input, 'https://github.com/owner/repo');
    const button = screen.getByRole('button', { name: /Analyze Repository/i });
    expect((button as HTMLButtonElement).disabled).toBe(false);
  });

  it('shows a validation error for non-GitHub URLs', async () => {
    render(<JobSubmitForm onJobSubmitted={vi.fn()} />);
    const input = screen.getByLabelText(/GitHub Repository URL/i);
    await userEvent.type(input, 'https://gitlab.com/owner/repo');
    const button = screen.getByRole('button', { name: /Analyze Repository/i });
    fireEvent.click(button);
    await waitFor(() => {
      expect(screen.getByText(/must start with https:\/\/github\.com\//i)).toBeDefined();
    });
  });

  it('shows a validation error when submitting an empty URL', async () => {
    render(<JobSubmitForm onJobSubmitted={vi.fn()} />);
    // Force the form to submit by bypassing the disabled check via form submit event
    const form = screen.getByRole('form', { name: /Submit a new Cortex job/i });
    fireEvent.submit(form);
    await waitFor(() => {
      expect(screen.getByText(/Please enter a GitHub repository URL/i)).toBeDefined();
    });
  });

  it('calls onJobSubmitted after the hook reports a submitted job', async () => {
    const onJobSubmitted = vi.fn();

    // First render: no submittedJob yet
    vi.mocked(useSubmitJob).mockReturnValue(makeMockHook({ submittedJob: null }));

    const { rerender } = render(<JobSubmitForm onJobSubmitted={onJobSubmitted} />);

    // Simulate the hook updating with a completed submission
    vi.mocked(useSubmitJob).mockReturnValue(
      makeMockHook({ submittedJob: mockJob })
    );
    rerender(<JobSubmitForm onJobSubmitted={onJobSubmitted} />);

    await waitFor(() => {
      expect(onJobSubmitted).toHaveBeenCalledWith(mockJob);
    });
  });

  it('shows an API error message when the hook returns an error', () => {
    vi.mocked(useSubmitJob).mockReturnValue(
      makeMockHook({ error: 'Backend is offline' })
    );
    render(<JobSubmitForm onJobSubmitted={vi.fn()} />);
    expect(screen.getByText(/Backend is offline/i)).toBeDefined();
  });

  it('disables submit button while submitting', () => {
    vi.mocked(useSubmitJob).mockReturnValue(
      makeMockHook({ isSubmitting: true })
    );
    render(<JobSubmitForm onJobSubmitted={vi.fn()} />);
    const button = screen.getByRole('button', { name: /Submitting/i });
    expect((button as HTMLButtonElement).disabled).toBe(true);
  });
});
