// Copyright (C) 2024 Shatter-NC contributors
// SPDX-License-Identifier: AGPL-3.0-or-later

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import React from 'react';
import { ProbesPane } from '../components/machine-detail/ProbesPane';
import { probeParamsCacheKey } from '../components/machine-detail/probe/probeParams';

vi.mock('../contexts/WebSocketContext', () => ({
  useWebSocketContext: () => ({ subscribeProbeProgress: () => () => {} }),
}));

vi.mock('../components/machine-detail/probe/ProbeCyclePreview', () => ({
  ProbeCyclePreview: () => null,
}));

interface Call {
  url: string;
  body: Record<string, unknown>;
}

let calls: Call[] = [];

function jsonResponse(body: unknown): Response {
  return { ok: true, status: 200, json: async () => body } as Response;
}

beforeEach(() => {
  calls = [];
  localStorage.clear();
  global.fetch = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const body = init?.body ? JSON.parse(String(init.body)) : {};
    calls.push({ url, body });
    if (url.endsWith('/probe/write')) {
      return jsonResponse({ ok: true, macros_written: body.params, elapsed_s: 0.1 });
    }
    if (url.endsWith('/probe/start')) {
      return jsonResponse({ ok: true, target_program: 8110, elapsed_s: 0.1 });
    }
    if (url.endsWith('/probe/collect')) {
      return jsonResponse({ ok: true, results: { '100': 1.5 }, macros_written: { '900': 0 } });
    }
    return jsonResponse({ ok: true });
  }) as typeof fetch;
});

afterEach(() => cleanup());

const POISONED = { '900': 0, '901': 999, '902': 999, '903': 999 };

function field(machineId: number, macro: string): HTMLInputElement {
  return document.getElementById(`probe-param-${machineId}-${macro}`) as HTMLInputElement;
}

const writeCalls = () => calls.filter((c) => c.url.endsWith('/probe/write'));

describe('ProbesPane params', () => {
  it('accepts a typed negative distance and writes it to the macro', async () => {
    render(<ProbesPane machineId={1} macros={POISONED} machineStatus="standby" />);
    const x = field(1, '901');
    fireEvent.change(x, { target: { value: '-' } });
    expect(x.value).toBe('-');
    fireEvent.change(x, { target: { value: '-10' } });
    expect(x.value).toBe('-10');

    fireEvent.click(screen.getByRole('button', { name: '[ EXECUTE ]' }));
    await waitFor(() => expect(writeCalls()).toHaveLength(1));
    expect((writeCalls()[0].body.params as Record<string, number>)['901']).toBe(-10);
  });

  it('± toggles sign and EXECUTE is blocked while a field is incomplete', () => {
    render(<ProbesPane machineId={1} macros={POISONED} machineStatus="standby" />);
    fireEvent.click(screen.getByRole('button', { name: /Toggle sign of Z DIST/i }));
    expect(field(1, '903').value).toBe('-10');
    fireEvent.change(field(1, '902'), { target: { value: '-' } });
    expect(screen.getByRole('button', { name: '[ EXECUTE ]' })).toBeDisabled();
  });

  it('restores last-written values per machine after remount', async () => {
    const { unmount } = render(
      <ProbesPane machineId={1} macros={POISONED} machineStatus="standby" />
    );
    fireEvent.change(field(1, '901'), { target: { value: '-12.5' } });
    fireEvent.click(screen.getByRole('button', { name: '[ EXECUTE ]' }));
    await waitFor(() =>
      expect(localStorage.getItem(probeParamsCacheKey(1, 'corner_xyz', 'probe'))).toBeTruthy()
    );
    unmount();

    render(<ProbesPane machineId={1} macros={POISONED} machineStatus="standby" />);
    expect(field(1, '901').value).toBe('-12.5');
    cleanup();

    render(<ProbesPane machineId={2} macros={POISONED} machineStatus="standby" />);
    expect(field(2, '901').value).toBe('10');
  });

  it('falls back to defaults for an invalid cache entry', () => {
    localStorage.setItem(
      probeParamsCacheKey(1, 'corner_xyz', 'probe'),
      JSON.stringify({ v: 1, values: { '900': 0, '901': 'oops' } })
    );
    render(<ProbesPane machineId={1} macros={POISONED} machineStatus="standby" />);
    expect(field(1, '900').value).toBe('54');
    expect(field(1, '901').value).toBe('10');
  });

  it('RUN AGAIN after a successful cycle re-writes macros with the same values', async () => {
    render(<ProbesPane machineId={1} macros={POISONED} machineStatus="standby" />);
    fireEvent.change(field(1, '901'), { target: { value: '-10' } });
    fireEvent.click(screen.getByRole('button', { name: '[ EXECUTE ]' }));
    await screen.findByRole('button', { name: '[ NEXT ]' });
    fireEvent.click(screen.getByRole('button', { name: '[ NEXT ]' }));
    fireEvent.click(await screen.findByRole('button', { name: '[ START MOTION ]' }));
    fireEvent.click(await screen.findByRole('button', { name: '[ NEXT ]' }));
    const again = await screen.findByRole('button', { name: '[ RUN AGAIN ]' });
    expect(screen.getByRole('button', { name: '[ DONE ]' })).toBeInTheDocument();

    const exclusiveBefore = calls.filter((c) => c.url.endsWith('/probe/exclusive')).length;
    fireEvent.click(again);
    await waitFor(() => expect(writeCalls()).toHaveLength(2));
    expect((writeCalls()[1].body.params as Record<string, number>)['901']).toBe(-10);

    const exclusive = calls.filter((c) => c.url.endsWith('/probe/exclusive')).slice(exclusiveBefore);
    expect(exclusive.map((c) => c.body.active)).toEqual([false, true]);
    expect(screen.queryByText(/RESULTS \(#100\+\)/)).not.toBeInTheDocument();
  });

  it('DONE exits to the pane, where EXECUTE becomes RUN AGAIN', async () => {
    render(<ProbesPane machineId={1} macros={POISONED} machineStatus="standby" />);
    fireEvent.click(screen.getByRole('button', { name: '[ EXECUTE ]' }));
    fireEvent.click(await screen.findByRole('button', { name: '[ NEXT ]' }));
    fireEvent.click(await screen.findByRole('button', { name: '[ START MOTION ]' }));
    fireEvent.click(await screen.findByRole('button', { name: '[ NEXT ]' }));
    fireEvent.click(await screen.findByRole('button', { name: '[ DONE ]' }));
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: '[ RUN AGAIN ]' })).toBeEnabled();
  });
});
