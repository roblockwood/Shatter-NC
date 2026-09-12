import { describe, expect, it } from 'vitest';
import {
  buildProbeSim3D,
  motionAxes,
  motionLabel,
  pathCycleDurationMs,
  pathLength,
  PREVIEW_TRAVEL_MM_PER_S,
  samplePath,
} from '../components/machine-detail/probe/probeMotion';
import { probeCatalog } from '../data/probeCatalog';

/** Hits / measure segments ignore cycle Z bookends (start Z− / end Z+). */
function expectCycleBookends(path: { z: number }[]): void {
  expect(path[0].z).toBeGreaterThan(0);
  expect(path[path.length - 1].z).toBeGreaterThan(0);
  expect(path[1]).toMatchObject({ x: 0, y: 0, z: 0 });
}

describe('probeMotion 3D NC sim (machine-aligned)', () => {
  it('every cycle starts with Z− and ends with Z+', () => {
    for (const id of [
      'single_face_x_plus',
      'diameter_inside',
      'diameter_outside',
      'corner_xyz',
      'three_point_inside',
      'tool_length',
      'tool_length_multi',
    ] as const) {
      const params =
        id === 'corner_xyz'
          ? { '901': 12, '902': 15, '903': -6 }
          : id === 'diameter_outside'
            ? { '904': 40, '903': -8 }
            : id.startsWith('diameter') || id.startsWith('three')
              ? { '904': 40 }
              : {};
      const sim =
        id === 'tool_length_multi'
          ? buildProbeSim3D(id, params, { toolCount: 3 })
          : buildProbeSim3D(id, params);
      expectCycleBookends(sim.path);
      // First segment is pure Z−
      expect(sim.path[0].x).toBe(0);
      expect(sim.path[0].y).toBe(0);
      expect(sim.path[1].z).toBeLessThan(sim.path[0].z);
      // Last segment is pure Z+
      const a = sim.path[sim.path.length - 2];
      const b = sim.path[sim.path.length - 1];
      expect(Math.abs(a.x) < 1e-9 && Math.abs(a.y) < 1e-9).toBe(true);
      expect(b.z).toBeGreaterThan(a.z);
    }
  });

  it('tool_length_multi sequences multiple Z-Nano hits', () => {
    const one = buildProbeSim3D('tool_length_multi', {}, { toolCount: 1 });
    const three = buildProbeSim3D('tool_length_multi', {}, { toolCount: 3 });
    expect(one.path.filter((p) => p.hit)).toHaveLength(1);
    expect(three.path.filter((p) => p.hit)).toHaveLength(3);
    expect(pathLength(three.path)).toBeGreaterThan(pathLength(one.path));
  });

  it('inside diameter measures at jog Z (no invented plunge) — O8116 omits Z', () => {
    const sim = buildProbeSim3D('diameter_inside', { '904': 40 });
    expectCycleBookends(sim.path);
    const hits = sim.path.filter((p) => p.hit);
    expect(hits).toHaveLength(4);
    expect(hits.every((h) => Math.abs(h.z) < 1e-9)).toBe(true);
    expect(hits[0].x).toBeLessThan(0);
    expect(hits[1].x).toBeGreaterThan(0);
    expect(hits[2].y).toBeLessThan(0);
    expect(hits[3].y).toBeGreaterThan(0);
    // No measure-plane plunge (z < 0) on inside dia
    expect(sim.path.every((p) => p.z >= -1e-9)).toBe(true);
  });

  it('outside diameter Z-downs before each radial hit from clearance', () => {
    const sim = buildProbeSim3D('diameter_outside', { '904': 40, '903': -8 });
    const hits = sim.path.filter((p) => p.hit);
    expect(hits).toHaveLength(4);
    expect(hits.every((h) => h.z < 0)).toBe(true);
    // After bookend Z− to jog, first work move is lateral at clearance
    expect(sim.path[1].z).toBe(0);
    expect(sim.path[2].z).toBe(0);
  });

  it('corner_xyz hits mid-face on each wall (not the vertex)', () => {
    const sim = buildProbeSim3D('corner_xyz', {
      '901': 12,
      '902': 15,
      '903': -6,
    });
    expectCycleBookends(sim.path);
    const hits = sim.path.filter((p) => p.hit);
    expect(hits).toHaveLength(3);
    // XZ face: Y = 15, X inboard of corner
    expect(hits[0].y).toBe(15);
    expect(hits[0].x).toBeGreaterThan(12);
    expect(hits[0].z).toBe(-6);
    // YZ face: X = 12, Y inboard of corner
    expect(hits[1].x).toBe(12);
    expect(hits[1].y).toBeGreaterThan(15);
    expect(hits[1].z).toBe(-6);
    // XY top: on stock top (z=0), inboard of both walls — not buried at zm
    expect(hits[2].x).toBeGreaterThan(12);
    expect(hits[2].y).toBeGreaterThan(15);
    expect(hits[2].z).toBe(0);
    // Three distinct points — not piled on the vertex
    expect(hits[0].x !== hits[1].x || hits[0].y !== hits[1].y).toBe(true);

    // Side approach/touch are pure-axis; Z approach may be compound XY
    const zHitIdx = sim.path.findIndex(
      (p, i) => p.hit && i > 0 && Math.abs(p.z) < 1e-9
    );
    expect(zHitIdx).toBeGreaterThan(0);
    const zApproach = sim.path[zHitIdx - 1];
    expect(zApproach.x).toBeGreaterThan(12);
    expect(zApproach.y).toBeGreaterThan(15);
    // Compound XY from origin column (same Z raise) onto the top approach point
    const zRaiseIdx = zHitIdx - 2;
    expect(sim.path[zRaiseIdx]).toMatchObject({ x: 0, y: 0 });
    expect(Math.abs(zApproach.x) > 1e-6 && Math.abs(zApproach.y) > 1e-6).toBe(
      true
    );
    expect(Math.abs(zApproach.z - sim.path[zRaiseIdx].z) < 1e-6).toBe(true);

    for (let i = 1; i < sim.path.length; i++) {
      const a = sim.path[i - 1];
      const b = sim.path[i];
      if (b.kind === 'rapid') continue;
      // Allow the one compound XY Z-approach segment
      if (i === zHitIdx - 1) {
        const dx = Math.abs(b.x - a.x) > 1e-6;
        const dy = Math.abs(b.y - a.y) > 1e-6;
        const dz = Math.abs(b.z - a.z) > 1e-6;
        expect(dx && dy && !dz).toBe(true);
        continue;
      }
      const axes =
        (Math.abs(b.x - a.x) > 1e-6 ? 1 : 0) +
        (Math.abs(b.y - a.y) > 1e-6 ? 1 : 0) +
        (Math.abs(b.z - a.z) > 1e-6 ? 1 : 0);
      expect(axes).toBeLessThanOrEqual(1);
    }
    // After first hit: retract along probe axis to approach, then Z, then home
    const firstHitIdx = sim.path.findIndex((p) => p.hit);
    const approach = sim.path[firstHitIdx - 1];
    expect(sim.path[firstHitIdx + 1]).toMatchObject({
      x: approach.x,
      y: approach.y,
      z: approach.z,
      kind: 'rapid',
    });
    expect(sim.path[firstHitIdx + 2]).toMatchObject({
      x: approach.x,
      y: approach.y,
      z: 0,
      kind: 'rapid',
    });

    // After bookend: jog → measure Z → X mid-face → pure Y touch
    expect(sim.path[1]).toMatchObject({ x: 0, y: 0, z: 0 });
    expect(sim.path[2]).toMatchObject({ x: 0, y: 0, z: -6 });
    expect(sim.path[3].x).toBeGreaterThan(12);
    expect(sim.path[3]).toMatchObject({ y: 0, z: -6 });
    expect(sim.path[4].hit).toBe(true);
    expect(sim.path[4].y).toBe(15);
  });

  it('single face X probes at jog Z — O8103 omits Z', () => {
    const sim = buildProbeSim3D('single_face_x_plus', {});
    expectCycleBookends(sim.path);
    const hit = sim.path.find((p) => p.hit);
    expect(hit).toMatchObject({ x: 15, y: 0, z: 0 });
    expect(sim.path.every((p) => p.z >= -1e-9)).toBe(true);
  });

  it('corner_xy probes at jog Z without #903', () => {
    const sim = buildProbeSim3D('corner_xy', { '901': 10, '902': 10 });
    const hits = sim.path.filter((p) => p.hit);
    expect(hits).toHaveLength(2);
    expect(hits.every((h) => Math.abs(h.z) < 1e-9)).toBe(true);
  });

  it('three-point inside stays at jog Z; uses H/U/V angles', () => {
    const sim = buildProbeSim3D('three_point_inside', {
      '904': 40,
      '905': 0,
      '906': 90,
      '907': 180,
    });
    expectCycleBookends(sim.path);
    const hits = sim.path.filter((p) => p.hit);
    expect(hits).toHaveLength(3);
    expect(hits.every((h) => Math.abs(h.z) < 1e-9)).toBe(true);
    expect(hits[0].x).toBeGreaterThan(0);
    expect(hits[1].y).toBeGreaterThan(0);
    expect(hits[2].x).toBeLessThan(0);
  });

  it('width inside stays at jog Z', () => {
    const sim = buildProbeSim3D('width_inside_x', { '904': 40 });
    expectCycleBookends(sim.path);
    expect(sim.path.filter((p) => p.hit)).toHaveLength(2);
    expect(sim.path.every((p) => p.z >= -1e-9)).toBe(true);
  });

  it('samplePath dwells on hit with zero dir, servo-accel then cruise, then continues', () => {
    const sim = buildProbeSim3D('single_face_x_plus', {});
    expect(pathLength(sim.path)).toBeGreaterThan(0);
    let sawHit = false;
    let sawDir = false;
    let hitHadZeroDir = false;
    let hitSamples = 0;
    for (let i = 0; i <= 80; i++) {
      const s = samplePath(sim.path, i / 80);
      if (s.onHit) {
        sawHit = true;
        hitSamples += 1;
        if (Math.hypot(s.dir.x, s.dir.y, s.dir.z) < 1e-6) hitHadZeroDir = true;
      }
      if (Math.abs(s.dir.x) > 0.5) sawDir = true;
    }
    expect(sawHit).toBe(true);
    expect(sawDir).toBe(true);
    expect(hitHadZeroDir).toBe(true);
    // Dwell is a meaningful fraction of the cycle (not a 1-frame flash)
    expect(hitSamples).toBeGreaterThan(4);
  });

  it('pathCycleDurationMs scales with path length (constant travel speed)', () => {
    const short = buildProbeSim3D('single_face_x_plus', {});
    const long = buildProbeSim3D('corner_xyz', {
      '901': 12,
      '902': 15,
      '903': -6,
    });
    const shortMs = pathCycleDurationMs(short.path);
    const longMs = pathCycleDurationMs(long.path);
    expect(longMs).toBeGreaterThan(shortMs * 1.5);
    // Roughly duration ≈ path mm / speed (plus dwells)
    const shortTravel = pathLength(short.path);
    expect(shortMs).toBeGreaterThan((shortTravel / PREVIEW_TRAVEL_MM_PER_S) * 1000);
  });

  it('outside diameter retracts along probe axis before Z (no XZ/YZ diagonal)', () => {
    const sim = buildProbeSim3D('diameter_outside', { '904': 40, '903': -8 });
    const firstHitIdx = sim.path.findIndex((p) => p.hit);
    expect(firstHitIdx).toBeGreaterThan(0);
    const approach = sim.path[firstHitIdx - 1];
    const back = sim.path[firstHitIdx + 1];
    // Undo G31 at measure Z first
    expect(back).toMatchObject({
      x: approach.x,
      y: approach.y,
      z: approach.z,
      kind: 'rapid',
    });
    // Then Z up at approach XY
    expect(sim.path[firstHitIdx + 2]).toMatchObject({
      x: approach.x,
      y: approach.y,
      z: 0,
      kind: 'rapid',
    });
    for (let i = 1; i < sim.path.length; i++) {
      const a = sim.path[i - 1];
      const b = sim.path[i];
      const dx = Math.abs(b.x - a.x) > 1e-6;
      const dy = Math.abs(b.y - a.y) > 1e-6;
      const dz = Math.abs(b.z - a.z) > 1e-6;
      expect(dz && (dx || dy)).toBe(false);
    }
  });

  it('corner with Z lines up mid-face before normal touch', () => {
    const sim = buildProbeSim3D('corner_xyz', {
      '901': 12,
      '902': 15,
      '903': -6,
    });
    // [0] bookend, [1] Z− to jog, [2] measure Z, [3] mid-face X, [4] hit
    expect(sim.path[1]).toMatchObject({ x: 0, y: 0, z: 0 });
    expect(sim.path[2]).toMatchObject({ x: 0, y: 0, z: -6 });
    expect(sim.path[3].x).toBeGreaterThan(12);
    expect(sim.path[3]).toMatchObject({ y: 0, z: -6 });
    expect(sim.path[4].hit).toBe(true);
    expect(sim.path[4].x).toBeGreaterThan(12);
  });

  it('three-point angled arms use XY combined moves (O8711)', () => {
    const sim = buildProbeSim3D('three_point_inside', {
      '904': 40,
      '905': 30,
      '906': 150,
      '907': 270,
    });
    // [0] bookend, [1] Z− to jog, [2] first arm
    const firstArm = sim.path[2];
    expect(Math.abs(firstArm.x) > 1e-6 && Math.abs(firstArm.y) > 1e-6).toBe(true);
    expect(Math.abs(firstArm.z) < 1e-6).toBe(true);
  });
});

describe('motionAxes', () => {
  it('reports combined axes instead of snapping to one', () => {
    const info = motionAxes({ x: 0.7, y: 0.7, z: 0 });
    expect(info.axes.map((a) => a.axis).sort()).toEqual(['x', 'y']);
    expect(motionLabel(info)).toContain('+X');
    expect(motionLabel(info)).toContain('+Y');
  });
});
