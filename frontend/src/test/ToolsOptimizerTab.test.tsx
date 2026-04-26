import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';
import { ToolsOptimizerTab } from '../components/machine-detail/ToolsOptimizerTab';

// Prevent actual fetch calls in unit tests
beforeEach(() => {
  global.fetch = vi.fn().mockResolvedValue({
    ok: false,
    json: async () => ({}),
  } as Response);
});

describe('ToolsOptimizerTab', () => {
  const baseProps = {
    machineId: 1,
    programName: 'O1234.NC',
    numPockets: 21,
    actualPotMap: new Map<number, number>(),
  };

  it('renders without crashing', () => {
    render(<ToolsOptimizerTab {...baseProps} />);
  });

  it('renders without crashing when machineId is undefined', () => {
    render(<ToolsOptimizerTab {...baseProps} machineId={undefined} />);
  });

  it('renders without crashing when programName is undefined', () => {
    render(<ToolsOptimizerTab {...baseProps} programName={undefined} />);
  });

  it('shows loading state while auto-analyzing on mount', () => {
    render(<ToolsOptimizerTab {...baseProps} />);
    expect(screen.getByText(/ANALYZING TOOL SEQUENCE/i)).toBeInTheDocument();
  });
});
