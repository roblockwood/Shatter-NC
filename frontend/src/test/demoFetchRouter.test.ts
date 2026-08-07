import { describe, expect, it } from 'vitest';
import { routeDemoFetch } from '../demo/demoFetchRouter';

describe('routeDemoFetch', () => {
  it('returns machine registry for GET /api/machines', async () => {
    const res = routeDemoFetch('http://demo.local/api/machines');
    expect(res?.status).toBe(200);
    const data = await res!.json();
    expect(Array.isArray(data)).toBe(true);
    expect(data.length).toBeGreaterThan(0);
    expect(data[0]).toHaveProperty('name');
  });

  it('returns programs listing for a machine', async () => {
    const res = routeDemoFetch('http://demo.local/api/machines/1/programs?path=/');
    expect(res?.status).toBe(200);
    const data = await res!.json();
    expect(Array.isArray(data)).toBe(true);
    expect(data.some((p: { name: string }) => p.name === 'O1234.NC')).toBe(true);
  });

  it('blocks mutations with 403', async () => {
    const res = routeDemoFetch('http://demo.local/api/machines/1', { method: 'DELETE' });
    expect(res?.status).toBe(403);
    const data = await res!.json();
    expect(data.detail).toMatch(/Demo mode/i);
  });

  it('returns running summary', async () => {
    const res = routeDemoFetch('http://demo.local/api/summary/running?time_range=24h');
    expect(res?.status).toBe(200);
    const data = await res!.json();
    expect(data).toHaveProperty('machines');
  });

  it('returns production runs as array', async () => {
    const res = routeDemoFetch(
      'http://demo.local/api/machines/1/production-runs-timeline?start_time=2026-01-01T00:00:00Z&end_time=2026-12-31T00:00:00Z',
    );
    expect(res?.status).toBe(200);
    const data = await res!.json();
    expect(Array.isArray(data)).toBe(true);
  });

  it('returns rich PRD3 status history as a paginated array', async () => {
    const res = routeDemoFetch(
      'http://demo.local/api/machines/1/prd3-status-history?limit=100&offset=0',
    );
    expect(res?.status).toBe(200);
    const data = await res!.json();
    expect(Array.isArray(data)).toBe(true);
    expect(data.length).toBeGreaterThan(20);
    expect(data[0]).toMatchObject({
      status: expect.any(String),
      start_time: expect.any(String),
      label: expect.any(String),
      duration_seconds: expect.any(Number),
    });
  });

  it('returns empty alarms array for machines without active faults', async () => {
    const res = routeDemoFetch('http://demo.local/api/machines/1/alarms');
    expect(res?.status).toBe(200);
    const data = await res!.json();
    expect(Array.isArray(data)).toBe(true);
    expect(data.length).toBeGreaterThan(0);
  });
});
