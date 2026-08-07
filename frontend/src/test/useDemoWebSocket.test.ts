import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useDemoWebSocket } from '../demo/useDemoWebSocket';

describe('useDemoWebSocket', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('starts connected with demo fleet', () => {
    const { result } = renderHook(() => useDemoWebSocket());
    expect(result.current.isConnected).toBe(true);
    expect(result.current.machines.length).toBe(3);
    expect(result.current.compressors.length).toBe(1);
    expect(result.current.machines[0].machine_name).toBe('Mill-01');
  });

  it('ticks operating machine counters over time', () => {
    const { result } = renderHook(() => useDemoWebSocket());
    const initialCount = result.current.machines.find((m) => m.machine_id === 1)?.counters?.[0]?.count;
    act(() => {
      vi.advanceTimersByTime(4000);
    });
    const nextCount = result.current.machines.find((m) => m.machine_id === 1)?.counters?.[0]?.count;
    expect(nextCount).toBeGreaterThan(initialCount ?? 0);
  });
});
