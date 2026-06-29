// =============================================================================
// StatusBadge Tests
// =============================================================================

import React from 'react';
import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import StatusBadge from './StatusBadge';
import type { JobStatus } from '@/types';

const ALL_STATUSES: JobStatus[] = ['pending', 'running', 'completed', 'failed', 'cancelled'];

describe('StatusBadge', () => {
  it.each(ALL_STATUSES)('renders correct text for status: %s', (status) => {
    render(<StatusBadge status={status} />);
    const badge = screen.getByTestId('status-badge');
    const expectedLabel = status.charAt(0).toUpperCase() + status.slice(1);
    expect(badge.textContent).toContain(expectedLabel);
  });

  it('applies yellow color class for pending status', () => {
    render(<StatusBadge status="pending" />);
    const badge = screen.getByTestId('status-badge');
    expect(badge.className).toContain('yellow');
  });

  it('applies blue color class for running status', () => {
    render(<StatusBadge status="running" />);
    const badge = screen.getByTestId('status-badge');
    expect(badge.className).toContain('blue');
  });

  it('applies green color class for completed status', () => {
    render(<StatusBadge status="completed" />);
    const badge = screen.getByTestId('status-badge');
    expect(badge.className).toContain('green');
  });

  it('applies red color class for failed status', () => {
    render(<StatusBadge status="failed" />);
    const badge = screen.getByTestId('status-badge');
    expect(badge.className).toContain('red');
  });

  it('applies gray color class for cancelled status', () => {
    render(<StatusBadge status="cancelled" />);
    const badge = screen.getByTestId('status-badge');
    expect(badge.className).toContain('gray');
  });

  it('renders animated pulse dot for running status', () => {
    render(<StatusBadge status="running" />);
    // The pulse dot uses animate-ping class
    const pulseDot = document.querySelector('.animate-ping');
    expect(pulseDot).not.toBeNull();
  });

  it('does not render pulse dot for non-running statuses', () => {
    render(<StatusBadge status="completed" />);
    const pulseDot = document.querySelector('.animate-ping');
    expect(pulseDot).toBeNull();
  });

  it('accepts and applies an extra className', () => {
    render(<StatusBadge status="pending" className="my-custom-class" />);
    const badge = screen.getByTestId('status-badge');
    expect(badge.className).toContain('my-custom-class');
  });

  it('sets the data-status attribute to the job status value', () => {
    render(<StatusBadge status="failed" />);
    const badge = screen.getByTestId('status-badge');
    expect(badge.getAttribute('data-status')).toBe('failed');
  });
});
