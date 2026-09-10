/**
 * NC-inspired 3D probe path simulator for Shatter Probes preview.
 *
 * Aligned to Blum V4A on this site (O8700 → O8701 / O8702 / O8711; O8717 TC):
 * - sphere_r = 1.5 mm (O8717 #3/#4)
 * - vacant R = 10 mm (O8702 / O8711)
 * - Preview truncates at contact — no G31 overtravel (TC #5/#6 strokes omitted)
 *
 * Z rule (machine): vacant #903 / Z → stay at jog Z. Preview maps jog/clearance
 * to z=0 and only plunges when the helper actually passes Z.
 * - face X/Y, corner XY, width inside, dia inside, 3pt inside: measure at z=0
 * - face Z / corner with Z / width·dia·obstacle outside / 3pt outside: use #903
 *
 * Coordinates: z=0 = jog/clearance. Measure plane z=-|#903| when Z is present.
 * Every cycle bookends with Z− from a raised start down to jog, and Z+ home
 * at the end. Stock tops sit **above** the measure height so side/OD touches
 * read as offset down from the rim (not coplanar with the top face).
 * Not a full G-code interpreter — kinematic sketch matching helper intent.
 */

export type Vec3 = { x: number; y: number; z: number };

export type SegKind = 'rapid' | 'feed' | 'touch';

export interface Waypoint extends Vec3 {
  /** Segment that arrives at this point */
  kind: SegKind;
  /** True when this point is the G31 skip hit */
  hit?: boolean;
}

export type Feature3D =
  | { kind: 'box'; cx: number; cy: number; cz: number; sx: number; sy: number; sz: number }
  | { kind: 'cylinder'; cx: number; cy: number; cz: number; r: number; h: number }
  | {
      kind: 'plane';
      axis: 'x' | 'y' | 'z';
      at: number;
      u0: number;
      u1: number;
      v0: number;
      v1: number;
      /** Clearance / reference plane — drawn dashed and faint */
      reference?: boolean;
    }
  | { kind: 'walls_x'; xNeg: number; xPos: number; y0: number; y1: number; z0: number; z1: number }
  | { kind: 'walls_y'; yNeg: number; yPos: number; x0: number; x1: number; z0: number; z1: number };

export interface ProbeSim3D {
  path: Waypoint[];
  features: Feature3D[];
  labels: { text: string; at: Vec3 }[];
}

/** O8717 PROBESPHERERADIUS XY/Z on this site */
const SPHERE_R = 1.5;
/** O8702 / O8711 vacant-R default */
const R_DEFAULT = 10;

function n(v: number | undefined, fallback: number): number {
  if (v == null || !Number.isFinite(v)) return fallback;
  return v;
}

function abs(v: number | undefined, fallback: number): number {
  const x = n(v, fallback);
  return Math.abs(x) < 1e-9 ? fallback : Math.abs(x);
}

/**
 * Measure-plane Z. Vacant #903 → 0 (jog/clearance) per O8701/O8702/O8711.
 * Present → negative magnitude (start above feature).
 */
function measureZ(zParam: number | undefined): number {
  if (zParam != null && Number.isFinite(zParam) && Math.abs(zParam) > 1e-9) {
    return -Math.abs(zParam);
  }
  return 0;
}

function push(
  path: Waypoint[],
  p: Vec3,
  kind: SegKind,
  hit = false
): void {
  path.push({ ...p, kind, hit });
}

/** Raised Z above jog/clearance — every cycle opens with Z− and closes with Z+. */
const CYCLE_Z_BOOKEND = 10;

function startCycle(): Waypoint[] {
  return [{ x: 0, y: 0, z: CYCLE_Z_BOOKEND, kind: 'rapid' }];
}

/** First motion of every cycle: Z− from bookend down to jog/clearance. */
function plungeBookendToJog(path: Waypoint[]): void {
  push(path, { x: 0, y: 0, z: 0 }, 'feed');
}

/** Final motion of every cycle: home XY if needed, then Z+ to bookend. */
function endCycle(path: Waypoint[]): void {
  const last = path[path.length - 1];
  if (!last) {
    push(path, { x: 0, y: 0, z: CYCLE_Z_BOOKEND }, 'rapid');
    return;
  }
  if (Math.abs(last.x) > 1e-9 || Math.abs(last.y) > 1e-9) {
    if (last.z < -1e-9) {
      push(path, { x: last.x, y: last.y, z: 0 }, 'rapid');
    }
    const cur = path[path.length - 1]!;
    const zKeep = cur.z > 1e-9 ? cur.z : 0;
    push(path, { x: 0, y: 0, z: zKeep }, 'rapid');
  }
  const at = path[path.length - 1]!;
  if (at.z < -1e-9) {
    push(path, { x: 0, y: 0, z: 0 }, 'rapid');
  }
  const home = path[path.length - 1]!;
  if (Math.abs(home.z - CYCLE_Z_BOOKEND) > 1e-9) {
    push(path, { x: 0, y: 0, z: CYCLE_Z_BOOKEND }, 'rapid');
  }
}

/** Plunge centerline from clearance (z=0) to measure plane (only when zm < 0). */
function plungeToMeasure(path: Waypoint[], zm: number): void {
  if (zm >= -1e-9) return;
  push(path, { x: 0, y: 0, z: zm }, 'feed');
}

/** Retract to clearance plane at XY of last point (or center). */
function retractToClearance(path: Waypoint[], x = 0, y = 0): void {
  const last = path[path.length - 1];
  if (last && Math.abs(last.z) < 1e-9 && last.x === x && last.y === y) return;
  push(path, { x, y, z: 0 }, 'rapid');
}

/**
 * After G31: return to the unprotected probe-move origin first (undo the
 * touch along its axis), then Z up to clearance if the approach was below
 * jog (measure plane). Typical: X+ → HIT → X− to approach → Z up.
 */
function retractAfterTouch(path: Waypoint[], approach: Vec3): void {
  const last = path[path.length - 1];
  if (!last) return;
  if (
    Math.abs(last.x - approach.x) > 1e-9 ||
    Math.abs(last.y - approach.y) > 1e-9 ||
    Math.abs(last.z - approach.z) > 1e-9
  ) {
    push(
      path,
      { x: approach.x, y: approach.y, z: approach.z },
      'rapid'
    );
  }
  // Only climb to clearance when approach was a measure-plane pose (z < 0)
  if (approach.z < -1e-9) {
    push(path, { x: approach.x, y: approach.y, z: 0 }, 'rapid');
  }
}

/** Rapid to XY; drops to clearance only when currently below z=0. */
function rapidXYClearance(path: Waypoint[], x: number, y: number): void {
  const last = path[path.length - 1];
  if (!last) {
    push(path, { x, y, z: 0 }, 'rapid');
    return;
  }
  if (last.z < -1e-9) {
    push(path, { x: last.x, y: last.y, z: 0 }, 'rapid');
  }
  const cur = path[path.length - 1]!;
  const zKeep = cur.z > 1e-9 ? cur.z : 0;
  if (Math.abs(cur.x - x) > 1e-9 || Math.abs(cur.y - y) > 1e-9) {
    push(path, { x, y, z: zKeep }, 'rapid');
  }
}

function clearancePlaneFeature(span = 28): Feature3D {
  return {
    kind: 'plane',
    axis: 'z',
    at: 0,
    u0: -span / 2,
    u1: span / 2,
    v0: -span / 2,
    v1: span / 2,
    reference: true,
  };
}

/**
 * Part top vs measure height:
 * - Stock top sits at clearance (z=0) when #903 plunges below — stylus is offset down.
 * - When measuring at jog Z (no #903), stock shows a short crown above z=0 so the
 *   stylus is still visually below the rim (same idea as single-face plane extents).
 */
const STOCK_CROWN_WHEN_AT_JOG = 6;

function stockTopZ(measureZ: number): number {
  return measureZ < -1e-9 ? 0 : STOCK_CROWN_WHEN_AT_JOG;
}

/** Box with top above the measure height; body extends downward past zm. */
function stockBox(
  cx: number,
  cy: number,
  zm: number,
  sx: number,
  sy: number,
  depthBelow = 16
): Feature3D {
  const top = stockTopZ(zm);
  const bottom = Math.min(zm, 0) - Math.max(depthBelow, 8);
  const sz = Math.max(top - bottom, 8);
  return { kind: 'box', cx, cy, cz: (top + bottom) / 2, sx, sy, sz };
}

/** Cylinder with top above the measure height; body extends downward past zm. */
function stockCylinder(
  cx: number,
  cy: number,
  zm: number,
  r: number,
  depthBelow = 16
): Feature3D {
  const top = stockTopZ(zm);
  const bottom = Math.min(zm, 0) - Math.max(depthBelow, 8);
  const h = Math.max(top - bottom, 8);
  return { kind: 'cylinder', cx, cy, cz: (top + bottom) / 2, r, h };
}

/**
 * Obstacle routines: part rim and boss sit under clearance so the jog path
 * clears both. Rim is lowered and boss raised to split the former gap
 * (rim at z=0 vs boss buried near measure).
 */
function obstacleWallTopZ(zm: number): number {
  if (zm >= -1e-9) return -2;
  return zm * 0.22; // e.g. zm=-8 → ~-1.8
}

function obstacleTopZ(zm: number): number {
  if (zm >= -1e-9) return -4;
  return zm * 0.48; // e.g. zm=-8 → ~-3.8 (above measure, below rim)
}

function cylinderToTop(
  cx: number,
  cy: number,
  top: number,
  zm: number,
  r: number,
  depthBelow = 16
): Feature3D {
  const bottom = Math.min(zm, 0) - Math.max(depthBelow, 8);
  const h = Math.max(top - bottom, 6);
  return { kind: 'cylinder', cx, cy, cz: (top + bottom) / 2, r, h };
}

function obstacleBox(
  cx: number,
  cy: number,
  zm: number,
  sx: number,
  sy: number,
  depthBelow = 12
): Feature3D {
  const top = obstacleTopZ(zm);
  const bottom = Math.min(zm, 0) - Math.max(depthBelow, 8);
  const sz = Math.max(top - bottom, 6);
  return { kind: 'box', cx, cy, cz: (top + bottom) / 2, sx, sy, sz };
}

function obstacleCylinder(
  cx: number,
  cy: number,
  zm: number,
  r: number,
  depthBelow = 12
): Feature3D {
  return cylinderToTop(cx, cy, obstacleTopZ(zm), zm, r, depthBelow);
}

function obstacleWallsZ(zm: number): { z0: number; z1: number } {
  return {
    z0: Math.min(zm, 0) - 16,
    z1: obstacleWallTopZ(zm),
  };
}

function stockWallsZ(zm: number): { z0: number; z1: number } {
  return {
    z0: Math.min(zm, 0) - 16,
    z1: stockTopZ(zm),
  };
}

/**
 * Single-face (O8103–07 → O8701).
 * X/Y wrappers omit Z → probe at jog Z. Z face uses baked Z-15.
 */
function singleFace(axis: 'x' | 'y' | 'z', signedDist: number): ProbeSim3D {
  const d = signedDist;
  const path: Waypoint[] = startCycle();
  plungeBookendToJog(path);
  const features: Feature3D[] = [clearancePlaneFeature()];

  if (axis === 'z') {
    const hitZ = d < 0 ? d : -15;
    push(path, { x: 0, y: 0, z: hitZ }, 'touch', true);
    retractToClearance(path);
    endCycle(path);
    features.push({
      kind: 'plane',
      axis: 'z',
      at: hitZ,
      u0: -12,
      u1: 12,
      v0: -12,
      v1: 12,
    });
    return {
      path,
      features,
      labels: [{ text: 'Z', at: { x: 0, y: 0, z: hitZ / 2 } }],
    };
  }

  // X/Y at jog Z (z=0) — matches wrappers with no Z arg
  const hit: Vec3 =
    axis === 'x' ? { x: d, y: 0, z: 0 } : { x: 0, y: d, z: 0 };
  push(path, hit, 'touch', true);
  push(path, { x: 0, y: 0, z: 0 }, 'rapid');
  endCycle(path);

  features.push({
    kind: 'plane',
    axis,
    at: d,
    u0: -12,
    u1: 12,
    v0: -16,
    v1: 4,
  });
  return {
    path,
    features,
    labels: [{ text: axis.toUpperCase(), at: { x: hit.x / 2, y: hit.y / 2, z: 2 } }],
  };
}

/**
 * Corner probe — mid-face contacts with pure-axis approach/touch (preview).
 *
 * Outside corner of stock at (xt, yt); start at origin in free space.
 * A stylus cannot land on the geometric vertex — each arm hits **on that
 * face**, inset from the edges:
 *   1. XZ plane (Y = yt): line up inboard in X, touch with pure Y
 *   2. YZ plane (X = xt): line up inboard in Y, touch with pure X
 *   3. XY plane (stock top): compound XY over top inboard, then pure Z touch
 *
 * After each hit: retract along the probe axis to the touch origin, then Z
 * to clearance, then home XY — not Z-first off the face.
 */
function corner(dx: number | null, dy: number | null, dz: number | null): ProbeSim3D {
  const path: Waypoint[] = startCycle();
  plungeBookendToJog(path);
  const xt = dx ?? 0;
  const yt = dy ?? 0;
  const hasX = dx != null && Math.abs(dx) > 1e-9;
  const hasY = dy != null && Math.abs(dy) > 1e-9;
  const hasZ = dz != null && Math.abs(dz) > 1e-9;
  const zm = hasZ ? (dz as number) : 0;
  const sxDir = Math.sign(xt || 1) || 1;
  const syDir = Math.sign(yt || 1) || 1;
  const sideZ = zm; // jog Z when no #903
  const topZ = stockTopZ(sideZ);

  // Mid-face insets: far enough from the vertex that hits read as face contacts
  const boxXY = 32;
  const faceMid = boxXY * 0.4;
  const xzHitX = hasX ? xt + sxDir * faceMid : sxDir * faceMid; // on XZ wall
  const yzHitY = hasY ? yt + syDir * faceMid : syDir * faceMid; // on YZ wall
  const xyHitX = hasX ? xt + sxDir * faceMid * 0.5 : sxDir * faceMid * 0.5;
  const xyHitY = hasY ? yt + syDir * faceMid * 0.5 : syDir * faceMid * 0.5;

  const finishArm = (approach: Vec3): void => {
    retractAfterTouch(path, approach);
    rapidXYClearance(path, 0, 0);
  };

  // 1) XZ face — mid-face in X, touch along +Y (face normal)
  if (hasY) {
    if (Math.abs(sideZ) > 1e-9) {
      push(path, { x: 0, y: 0, z: sideZ }, 'feed');
    }
    const approach = { x: xzHitX, y: 0, z: sideZ };
    push(path, approach, 'feed');
    push(path, { x: xzHitX, y: yt, z: sideZ }, 'touch', true);
    finishArm(approach);
  }

  // 2) YZ face — mid-face in Y, touch along +X (face normal)
  if (hasX) {
    if (Math.abs(sideZ) > 1e-9) {
      push(path, { x: 0, y: 0, z: sideZ }, 'feed');
    }
    const approach = { x: 0, y: yzHitY, z: sideZ };
    push(path, approach, 'feed');
    push(path, { x: xt, y: yzHitY, z: sideZ }, 'touch', true);
    finishArm(approach);
  }

  // 3) XY face — raise, compound-XY over inboard top, pure Z touch
  if (hasZ) {
    const zRaise = topZ + Math.max(Math.abs(zm), 8);
    const approach = { x: xyHitX, y: xyHitY, z: zRaise };
    push(path, { x: 0, y: 0, z: zRaise }, 'feed');
    push(path, approach, 'feed'); // compound XY
    push(path, { x: xyHitX, y: xyHitY, z: topZ }, 'touch', true);
    finishArm(approach);
  }

  endCycle(path);

  const depth = Math.max(boxXY, 16);
  const cx = hasX ? xt + sxDir * (boxXY / 2) : sxDir * (boxXY / 2);
  const cy = hasY ? yt + syDir * (boxXY / 2) : syDir * (boxXY / 2);
  const features: Feature3D[] = [
    clearancePlaneFeature(Math.max(48, boxXY + Math.abs(xt) + Math.abs(yt) + 8)),
    stockBox(cx, cy, sideZ, boxXY, boxXY, depth),
  ];
  const tag = [hasX && 'X', hasY && 'Y', hasZ && 'Z'].filter(Boolean).join('') || 'COR';
  return {
    path,
    features,
    labels: [{ text: tag, at: { x: xt / 2, y: yt / 2, z: 2 } }],
  };
}

/** Inside width (O8112/13): no Z → probe at jog Z; vacant R = 10. */
function widthInside(axis: 'x' | 'y', size: number): ProbeSim3D {
  const half = size / 2;
  const inset = Math.max(half - SPHERE_R - R_DEFAULT, half * 0.25);
  const zm = 0;
  const path: Waypoint[] = startCycle();
  plungeBookendToJog(path);

  if (axis === 'x') {
    const a0 = { x: -inset, y: 0, z: zm };
    const a1 = { x: inset, y: 0, z: zm };
    push(path, a0, 'feed');
    push(path, { x: -half + SPHERE_R, y: 0, z: zm }, 'touch', true);
    retractAfterTouch(path, a0);
    rapidXYClearance(path, 0, 0);
    push(path, a1, 'feed');
    push(path, { x: half - SPHERE_R, y: 0, z: zm }, 'touch', true);
    retractAfterTouch(path, a1);
    rapidXYClearance(path, 0, 0);
  } else {
    const a0 = { x: 0, y: -inset, z: zm };
    const a1 = { x: 0, y: inset, z: zm };
    push(path, a0, 'feed');
    push(path, { x: 0, y: -half + SPHERE_R, z: zm }, 'touch', true);
    retractAfterTouch(path, a0);
    rapidXYClearance(path, 0, 0);
    push(path, a1, 'feed');
    push(path, { x: 0, y: half - SPHERE_R, z: zm }, 'touch', true);
    retractAfterTouch(path, a1);
    rapidXYClearance(path, 0, 0);
  }

  endCycle(path);

  const features: Feature3D[] = [
    clearancePlaneFeature(),
    axis === 'x'
      ? {
          kind: 'walls_x',
          xNeg: -half,
          xPos: half,
          y0: -10,
          y1: 10,
          ...stockWallsZ(zm),
        }
      : {
          kind: 'walls_y',
          yNeg: -half,
          yPos: half,
          x0: -10,
          x1: 10,
          ...stockWallsZ(zm),
        },
  ];

  return {
    path,
    features,
    labels: [{ text: 'W', at: { x: 0, y: 0, z: 4 } }],
  };
}

/** Outside width: lateral at clearance, Z-down each side (O8702). */
function widthOutside(axis: 'x' | 'y', size: number, zm: number): ProbeSim3D {
  const half = size / 2;
  const outset = half + SPHERE_R + R_DEFAULT;
  const path: Waypoint[] = startCycle();
  plungeBookendToJog(path);

  if (axis === 'x') {
    const a0 = { x: -outset, y: 0, z: zm };
    const a1 = { x: outset, y: 0, z: zm };
    push(path, { x: -outset, y: 0, z: 0 }, 'feed');
    push(path, a0, 'feed');
    push(path, { x: -half - SPHERE_R, y: 0, z: zm }, 'touch', true);
    retractAfterTouch(path, a0);
    push(path, { x: outset, y: 0, z: 0 }, 'feed');
    push(path, a1, 'feed');
    push(path, { x: half + SPHERE_R, y: 0, z: zm }, 'touch', true);
    retractAfterTouch(path, a1);
    rapidXYClearance(path, 0, 0);
  } else {
    const a0 = { x: 0, y: -outset, z: zm };
    const a1 = { x: 0, y: outset, z: zm };
    push(path, { x: 0, y: -outset, z: 0 }, 'feed');
    push(path, a0, 'feed');
    push(path, { x: 0, y: -half - SPHERE_R, z: zm }, 'touch', true);
    retractAfterTouch(path, a0);
    push(path, { x: 0, y: outset, z: 0 }, 'feed');
    push(path, a1, 'feed');
    push(path, { x: 0, y: half + SPHERE_R, z: zm }, 'touch', true);
    retractAfterTouch(path, a1);
    rapidXYClearance(path, 0, 0);
  }

  endCycle(path);

  const features: Feature3D[] = [
    clearancePlaneFeature(),
    stockBox(0, 0, zm, axis === 'x' ? size : 12, axis === 'y' ? size : 12),
  ];
  return { path, features, labels: [{ text: 'W', at: { x: 0, y: 0, z: 4 } }] };
}

/** Inside 4-pt (O8116): no Z → all at jog Z. */
function diaInside4(size: number): ProbeSim3D {
  const half = size / 2;
  const inset = Math.max(half - SPHERE_R - R_DEFAULT, half * 0.2);
  const hitR = half - SPHERE_R;
  const zm = 0;
  const path: Waypoint[] = startCycle();
  plungeBookendToJog(path);

  const arms: Vec3[] = [
    { x: -inset, y: 0, z: zm },
    { x: inset, y: 0, z: zm },
    { x: 0, y: -inset, z: zm },
    { x: 0, y: inset, z: zm },
  ];
  const hits: Vec3[] = [
    { x: -hitR, y: 0, z: zm },
    { x: hitR, y: 0, z: zm },
    { x: 0, y: -hitR, z: zm },
    { x: 0, y: hitR, z: zm },
  ];

  for (let i = 0; i < 4; i++) {
    push(path, arms[i], 'feed');
    push(path, hits[i], 'touch', true);
    retractAfterTouch(path, arms[i]);
    rapidXYClearance(path, 0, 0);
  }

  endCycle(path);

  return {
    path,
    features: [clearancePlaneFeature(), stockCylinder(0, 0, zm, half)],
    labels: [{ text: 'DIA', at: { x: 0, y: 0, z: 4 } }],
  };
}

/** Outside 4-pt: lateral at clearance, Z-down each arm (O8702). */
function diaOutside4(size: number, zm: number): ProbeSim3D {
  const half = size / 2;
  const outset = half + SPHERE_R + R_DEFAULT;
  const hitR = half + SPHERE_R;
  const path: Waypoint[] = startCycle();
  plungeBookendToJog(path);

  const arms: Vec3[] = [
    { x: -outset, y: 0, z: 0 },
    { x: outset, y: 0, z: 0 },
    { x: 0, y: -outset, z: 0 },
    { x: 0, y: outset, z: 0 },
  ];
  const hits: Vec3[] = [
    { x: -hitR, y: 0, z: zm },
    { x: hitR, y: 0, z: zm },
    { x: 0, y: -hitR, z: zm },
    { x: 0, y: hitR, z: zm },
  ];

  for (let i = 0; i < 4; i++) {
    const approach = { x: arms[i].x, y: arms[i].y, z: zm };
    push(path, arms[i], 'feed');
    push(path, approach, 'feed');
    push(path, hits[i], 'touch', true);
    retractAfterTouch(path, approach);
  }
  rapidXYClearance(path, 0, 0);
  endCycle(path);

  return {
    path,
    features: [clearancePlaneFeature(), stockCylinder(0, 0, zm, half)],
    labels: [{ text: 'OD', at: { x: 0, y: 0, z: 4 } }],
  };
}

/**
 * Inside bore + obstacle: O8702 inside+Z (machine needs R < 0).
 * Preview uses |R| as obstacle clearance; write path negates positive UI values.
 */
function diaObstacle(size: number, zm: number, obstacle: number): ProbeSim3D {
  const half = size / 2;
  const obs = Math.min(abs(obstacle, 8) / 2, half * 0.55);
  const inset = Math.max((half + obs) / 2, obs + 2);
  const hitR = half - SPHERE_R;
  const path: Waypoint[] = startCycle();
  plungeBookendToJog(path);

  const arms: Vec3[] = [
    { x: -inset, y: 0, z: 0 },
    { x: inset, y: 0, z: 0 },
    { x: 0, y: -inset, z: 0 },
    { x: 0, y: inset, z: 0 },
  ];
  const hits: Vec3[] = [
    { x: -hitR, y: 0, z: zm },
    { x: hitR, y: 0, z: zm },
    { x: 0, y: -hitR, z: zm },
    { x: 0, y: hitR, z: zm },
  ];

  for (let i = 0; i < 4; i++) {
    const approach = { x: arms[i].x, y: arms[i].y, z: zm };
    push(path, arms[i], 'feed');
    push(path, approach, 'feed');
    push(path, hits[i], 'touch', true);
    retractAfterTouch(path, approach);
  }
  rapidXYClearance(path, 0, 0);
  endCycle(path);

  return {
    path,
    features: [
      clearancePlaneFeature(),
      cylinderToTop(0, 0, obstacleWallTopZ(zm), zm, half),
      obstacleCylinder(0, 0, zm, obs, 12),
    ],
    labels: [{ text: 'OBS', at: { x: 0, y: 0, z: 4 } }],
  };
}

function widthObstacle(axis: 'x' | 'y', size: number, zm: number, obstacle: number): ProbeSim3D {
  const half = size / 2;
  const obs = abs(obstacle, 8) / 2;
  const inset = Math.max(half - R_DEFAULT, obs + 3);
  const path: Waypoint[] = startCycle();
  plungeBookendToJog(path);

  if (axis === 'x') {
    const a0 = { x: -inset, y: 0, z: zm };
    const a1 = { x: inset, y: 0, z: zm };
    push(path, { x: -inset, y: 0, z: 0 }, 'feed');
    push(path, a0, 'feed');
    push(path, { x: -half + SPHERE_R, y: 0, z: zm }, 'touch', true);
    retractAfterTouch(path, a0);
    push(path, { x: inset, y: 0, z: 0 }, 'feed');
    push(path, a1, 'feed');
    push(path, { x: half - SPHERE_R, y: 0, z: zm }, 'touch', true);
    retractAfterTouch(path, a1);
    rapidXYClearance(path, 0, 0);
  } else {
    const a0 = { x: 0, y: -inset, z: zm };
    const a1 = { x: 0, y: inset, z: zm };
    push(path, { x: 0, y: -inset, z: 0 }, 'feed');
    push(path, a0, 'feed');
    push(path, { x: 0, y: -half + SPHERE_R, z: zm }, 'touch', true);
    retractAfterTouch(path, a0);
    push(path, { x: 0, y: inset, z: 0 }, 'feed');
    push(path, a1, 'feed');
    push(path, { x: 0, y: half - SPHERE_R, z: zm }, 'touch', true);
    retractAfterTouch(path, a1);
    rapidXYClearance(path, 0, 0);
  }

  endCycle(path);

  const features: Feature3D[] = [
    clearancePlaneFeature(),
    axis === 'x'
      ? {
          kind: 'walls_x',
          xNeg: -half,
          xPos: half,
          y0: -10,
          y1: 10,
          ...obstacleWallsZ(zm),
        }
      : {
          kind: 'walls_y',
          yNeg: -half,
          yPos: half,
          x0: -10,
          x1: 10,
          ...obstacleWallsZ(zm),
        },
    obstacleBox(0, 0, zm, axis === 'x' ? obs * 2 : 8, axis === 'y' ? obs * 2 : 8, 12),
  ];
  return { path, features, labels: [{ text: 'OBS', at: { x: 0, y: 0, z: 4 } }] };
}

/** 3-point: inside stays at jog Z; outside Z-downs each arm (O8711). */
function threePoint(
  size: number,
  angles: [number, number, number],
  outside: boolean,
  zm: number
): ProbeSim3D {
  const half = size / 2;
  const approachR = outside
    ? half + SPHERE_R + R_DEFAULT
    : Math.max(half - SPHERE_R - R_DEFAULT, half * 0.2);
  const hitR = outside ? half + SPHERE_R : half - SPHERE_R;
  const path: Waypoint[] = startCycle();
  plungeBookendToJog(path);
  const measureAt = outside ? zm : 0;

  if (outside) {
    // per-arm Z handled below
  } else {
    plungeToMeasure(path, measureAt); // no-op when measureAt === 0
  }

  for (const deg of angles) {
    const rad = (deg * Math.PI) / 180;
    const c = Math.cos(rad);
    const s = Math.sin(rad);
    if (outside) {
      const armClear = { x: approachR * c, y: approachR * s, z: 0 };
      const approach = { x: armClear.x, y: armClear.y, z: zm };
      const hit = { x: hitR * c, y: hitR * s, z: zm };
      push(path, armClear, 'feed'); // XY combined — O8711 P8703 X…Y…
      push(path, approach, 'feed'); // Z separate
      push(path, hit, 'touch', true); // XY combined G31
      retractAfterTouch(path, approach);
      rapidXYClearance(path, 0, 0);
    } else {
      const approach = { x: approachR * c, y: approachR * s, z: measureAt };
      const hit = { x: hitR * c, y: hitR * s, z: measureAt };
      push(path, approach, 'feed'); // XY combined
      push(path, hit, 'touch', true); // XY combined
      retractAfterTouch(path, approach);
      rapidXYClearance(path, 0, 0);
    }
  }

  endCycle(path);

  return {
    path,
    features: [clearancePlaneFeature(), stockCylinder(0, 0, measureAt, half)],
    labels: [{ text: '3PT', at: { x: 0, y: 0, z: 4 } }],
  };
}

/** Tool setter schematic (O8100 / O8915) — not spindle-probe kinematics. */
function toolLength(): ProbeSim3D {
  const path: Waypoint[] = startCycle();
  plungeBookendToJog(path);
  plungeToMeasure(path, -15);
  const last = path[path.length - 1];
  if (last) {
    last.kind = 'touch';
    last.hit = true;
  }
  retractToClearance(path);
  endCycle(path);
  return {
    path,
    features: [
      clearancePlaneFeature(24),
      { kind: 'box', cx: 0, cy: 0, cz: -16, sx: 22, sy: 22, sz: 4 },
    ],
    labels: [{ text: 'TOOL', at: { x: 0, y: 0, z: 4 } }],
  };
}

export function buildProbeSim3D(
  routineId: string,
  params: Record<string, number>
): ProbeSim3D {
  const x = n(params['901'], 10);
  const y = n(params['902'], 10);
  const zm = measureZ(params['903']);
  const size = abs(params['904'], 40);
  const m905 = n(params['905'], 10);
  const a1 = n(params['905'], 0);
  const a2 = n(params['906'], 120);
  const a3 = n(params['907'], 240);

  switch (routineId) {
    case 'tool_length':
      return toolLength();
    case 'single_face_x_plus':
      return singleFace('x', 15);
    case 'single_face_x_minus':
      return singleFace('x', -15);
    case 'single_face_y_plus':
      return singleFace('y', 15);
    case 'single_face_y_minus':
      return singleFace('y', -15);
    case 'single_face_z':
      return singleFace('z', -15);
    case 'corner_xy':
      return corner(x, y, null);
    case 'corner_xz':
      return corner(x, null, zm);
    case 'corner_yz':
      return corner(null, y, zm);
    case 'corner_xyz':
      return corner(x, y, zm);
    case 'width_inside_x':
      return widthInside('x', size);
    case 'width_inside_y':
      return widthInside('y', size);
    case 'width_outside_x':
      return widthOutside('x', size, zm);
    case 'width_outside_y':
      return widthOutside('y', size, zm);
    case 'diameter_inside':
      return diaInside4(size);
    case 'diameter_outside':
      return diaOutside4(size, zm);
    case 'obstacle_inside_dia':
      return diaObstacle(size, zm, m905);
    case 'obstacle_inside_width_x':
      return widthObstacle('x', size, zm, m905);
    case 'obstacle_inside_width_y':
      return widthObstacle('y', size, zm, m905);
    case 'three_point_inside':
      return threePoint(size, [a1, a2, a3], false, 0);
    case 'three_point_outside':
      return threePoint(size, [a1, a2, a3], true, zm);
    default: {
      const path = startCycle();
      plungeBookendToJog(path);
      push(path, { x: 10, y: 0, z: 0 }, 'touch', true);
      endCycle(path);
      return { path, features: [], labels: [] };
    }
  }
}

/**
 * Isometric projection (CNC Z-up; SVG Y grows downward).
 *
 * Machine +Y is negated in the view so the on-screen triad reads X+ / Y+ / Z+
 * in the usual mill sense (Y does not appear as Y− when X+ and Z+ look correct).
 */
export function projectView(p: Vec3, scale = 1): { x: number; y: number } {
  const x = p.x;
  const y = -p.y;
  const isoX = (x - y) * 0.8660254;
  const isoY = (x + y) * 0.5 - p.z;
  return { x: isoX * scale, y: isoY * scale };
}

export function pathLength(path: Waypoint[]): number {
  let total = 0;
  for (let i = 1; i < path.length; i++) {
    const a = path[i - 1];
    const b = path[i];
    total += Math.hypot(b.x - a.x, b.y - a.y, b.z - a.z);
  }
  return total;
}

/** Dominant signed machine axis for a direction vector. */
export function dominantMotionAxis(dir: Vec3): { axis: 'x' | 'y' | 'z'; sign: 1 | -1 } {
  const info = motionAxes(dir);
  if (info.axes.length) return info.axes[0];
  return { axis: 'x', sign: 1 };
}

export type MotionAxisId = 'x' | 'y' | 'z';

/** Axes participating in a move (for split-color direction arrows). */
export interface MotionInfo {
  axes: { axis: MotionAxisId; sign: 1 | -1 }[];
  /** Unit direction (or zero) */
  dir: Vec3;
}

/**
 * Which machine axes are meaningfully active on this segment.
 * Components within 35% of the largest count as combined (not snapped to one).
 */
export function motionAxes(dir: Vec3, ratio = 0.35): MotionInfo {
  const zero = { x: 0, y: 0, z: 0 };
  const comps: { axis: MotionAxisId; v: number }[] = [
    { axis: 'x', v: dir.x },
    { axis: 'y', v: dir.y },
    { axis: 'z', v: dir.z },
  ];
  const max = Math.max(Math.abs(dir.x), Math.abs(dir.y), Math.abs(dir.z));
  if (max < 1e-6) return { axes: [], dir: zero };
  const axes = comps
    .filter((c) => Math.abs(c.v) >= max * ratio)
    .sort((a, b) => Math.abs(b.v) - Math.abs(a.v))
    .map((c) => ({
      axis: c.axis,
      sign: (c.v >= 0 ? 1 : -1) as 1 | -1,
    }));
  const len = Math.hypot(dir.x, dir.y, dir.z) || 1;
  return {
    axes,
    dir: { x: dir.x / len, y: dir.y / len, z: dir.z / len },
  };
}

/** Title / HUD label e.g. +X, +Y+Z, -X+Y */
export function motionLabel(info: MotionInfo): string {
  if (!info.axes.length) return '';
  return info.axes
    .map((a) => `${a.sign < 0 ? '-' : '+'}${a.axis.toUpperCase()}`)
    .join('');
}

/**
 * Servo-like profile: accelerate over the first few mm, then cruise.
 * No ease-out — hard stop at the waypoint (hit dwell handles the pause).
 */
const ACCEL_DIST_MM = 5;

function accelDistance(len: number): number {
  if (len < 1e-9) return 0;
  // Cap so short segments still spend most of the move at cruise when possible
  return Math.min(ACCEL_DIST_MM, len * 0.4);
}

/**
 * Map linear time u∈[0,1] → distance fraction with a short accel ramp then
 * constant velocity (mimics servo motion systems).
 */
function easeServoMove(u: number, len: number): number {
  const x = Math.min(1, Math.max(0, u));
  const dA = accelDistance(len);
  if (dA < 1e-9 || len < 1e-9) return x;
  // Time share of accel so velocity is continuous into cruise (v: 0→cruise)
  const ta = (2 * dA) / (len + dA);
  const fA = dA / len;
  if (x <= ta) {
    const r = x / ta;
    return r * r * fA;
  }
  return fA + ((x - ta) / (1 - ta)) * (1 - fA);
}

/**
 * Preview cruise rate (mm/s). Cycle duration scales with path length so every
 * routine shares the same cruise speed — not a fixed period that stretches
 * short paths and rushes long ones. Accel adds a small time tax (~accel mm).
 */
export const PREVIEW_TRAVEL_MM_PER_S = 38;

/** Fixed wall-clock pause on each skip-hit (seconds). */
export const PREVIEW_HIT_DWELL_S = 0.45;

const MIN_SEG_WEIGHT = 0.06;

/** Rapids a bit quicker than feed/touch; still distance-based. */
function segSpeedWeight(kind: SegKind): number {
  if (kind === 'rapid') return 0.7;
  return 1;
}

type MovePhase = { kind: 'move'; i: number; weight: number; len: number };
type DwellPhase = { kind: 'dwell'; i: number; weight: number };
type Phase = MovePhase | DwellPhase;

function buildPathPhases(path: Waypoint[]): { phases: Phase[]; totalW: number } {
  if (path.length < 2) return { phases: [], totalW: 0 };

  const dwellW = PREVIEW_HIT_DWELL_S * PREVIEW_TRAVEL_MM_PER_S;
  const phases: Phase[] = [];
  let totalW = 0;
  for (let i = 1; i < path.length; i++) {
    const a = path[i - 1];
    const b = path[i];
    const len = Math.hypot(b.x - a.x, b.y - a.y, b.z - a.z);
    // Time ∝ L + d_accel at cruise speed (accel from rest costs one extra dA)
    const weight = Math.max(
      MIN_SEG_WEIGHT,
      (len + accelDistance(len)) * segSpeedWeight(b.kind)
    );
    phases.push({ kind: 'move', i, weight, len });
    totalW += weight;
    if (b.hit) {
      phases.push({ kind: 'dwell', i, weight: dwellW });
      totalW += dwellW;
    }
  }
  return { phases, totalW };
}

/** Loop period for a path at {@link PREVIEW_TRAVEL_MM_PER_S} (includes hit dwells). */
export function pathCycleDurationMs(path: Waypoint[]): number {
  const { totalW } = buildPathPhases(path);
  if (totalW < 1e-9) return 2000;
  return Math.max(1500, (totalW / PREVIEW_TRAVEL_MM_PER_S) * 1000);
}

/**
 * Sample path at normalized time t ∈ [0,1].
 *
 * Moves use a short servo-style accel then cruise — use
 * {@link pathCycleDurationMs} so wall-clock cruise speed is constant across
 * routines. Hard-stop on hit waypoints, dwell with `onHit`, then continue.
 * Zero dir while dwelling so the motion arrow hides during the blip.
 */
export function samplePath(
  path: Waypoint[],
  t: number
): { pos: Vec3; dir: Vec3; onHit: boolean; segKind: SegKind } {
  const zero = { x: 0, y: 0, z: 0 };
  if (!path.length) {
    return { pos: zero, dir: zero, onHit: false, segKind: 'rapid' };
  }
  if (path.length === 1) {
    return {
      pos: path[0],
      dir: zero,
      onHit: !!path[0].hit,
      segKind: path[0].kind,
    };
  }

  const { phases, totalW } = buildPathPhases(path);
  if (totalW < 1e-9) {
    return {
      pos: path[0],
      dir: zero,
      onHit: !!path[0].hit,
      segKind: path[0].kind,
    };
  }

  let remain = Math.min(1, Math.max(0, t)) * totalW;
  for (const phase of phases) {
    if (remain > phase.weight + 1e-12) {
      remain -= phase.weight;
      continue;
    }
    const b = path[phase.i];
    if (phase.kind === 'dwell') {
      return {
        pos: { x: b.x, y: b.y, z: b.z },
        dir: zero,
        onHit: true,
        segKind: b.kind,
      };
    }
    const a = path[phase.i - 1];
    const uLin = phase.weight < 1e-9 ? 1 : remain / phase.weight;
    const u = phase.len < 1e-9 ? 1 : easeServoMove(uLin, phase.len);
    const pos = {
      x: a.x + (b.x - a.x) * u,
      y: a.y + (b.y - a.y) * u,
      z: a.z + (b.z - a.z) * u,
    };
    const dir =
      phase.len < 1e-9
        ? zero
        : {
            x: (b.x - a.x) / phase.len,
            y: (b.y - a.y) / phase.len,
            z: (b.z - a.z) / phase.len,
          };
    // Hit only during the dwell that follows — not while still approaching
    return { pos, dir, onHit: false, segKind: b.kind };
  }

  const last = path[path.length - 1];
  return {
    pos: { x: last.x, y: last.y, z: last.z },
    dir: zero,
    onHit: !!last.hit,
    segKind: last.kind,
  };
}

/** Collect 3D points for viewBox fitting. */
export function collectSimPoints(sim: ProbeSim3D): Vec3[] {
  const pts: Vec3[] = sim.path.map((p) => ({ x: p.x, y: p.y, z: p.z }));
  for (const f of sim.features) {
    if (f.kind === 'box') {
      const hx = f.sx / 2;
      const hy = f.sy / 2;
      const hz = f.sz / 2;
      for (const dx of [-hx, hx])
        for (const dy of [-hy, hy])
          for (const dz of [-hz, hz])
            pts.push({ x: f.cx + dx, y: f.cy + dy, z: f.cz + dz });
    } else if (f.kind === 'cylinder') {
      for (let i = 0; i < 8; i++) {
        const a = (i / 8) * Math.PI * 2;
        pts.push({
          x: f.cx + f.r * Math.cos(a),
          y: f.cy + f.r * Math.sin(a),
          z: f.cz - f.h / 2,
        });
        pts.push({
          x: f.cx + f.r * Math.cos(a),
          y: f.cy + f.r * Math.sin(a),
          z: f.cz + f.h / 2,
        });
      }
    } else if (f.kind === 'plane') {
      if (f.axis === 'x') {
        pts.push({ x: f.at, y: f.u0, z: f.v0 }, { x: f.at, y: f.u1, z: f.v1 });
      } else if (f.axis === 'y') {
        pts.push({ x: f.u0, y: f.at, z: f.v0 }, { x: f.u1, y: f.at, z: f.v1 });
      } else {
        pts.push({ x: f.u0, y: f.v0, z: f.at }, { x: f.u1, y: f.v1, z: f.at });
      }
    } else if (f.kind === 'walls_x') {
      pts.push(
        { x: f.xNeg, y: f.y0, z: f.z0 },
        { x: f.xPos, y: f.y1, z: f.z1 }
      );
    } else {
      pts.push(
        { x: f.x0, y: f.yNeg, z: f.z0 },
        { x: f.x1, y: f.yPos, z: f.z1 }
      );
    }
  }
  return pts;
}

// Back-compat aliases used by older tests / imports
export type Point = { x: number; y: number };
export function buildProbeMotion(routineId: string, params: Record<string, number>) {
  const sim = buildProbeSim3D(routineId, params);
  const path2 = sim.path.map((p) => projectView(p));
  return {
    features: [] as never[],
    path: path2,
    labels: sim.labels.map((l) => ({ text: l.text, at: projectView(l.at) })),
    viewBox: { x: -20, y: -20, w: 40, h: 40 },
    sim,
  };
}

export function pointAlongPath(path: Point[], t: number): Point {
  if (!path.length) return { x: 0, y: 0 };
  if (path.length === 1) return path[0];
  let total = 0;
  const seglen: number[] = [];
  for (let i = 0; i < path.length - 1; i++) {
    const len = Math.hypot(path[i + 1].x - path[i].x, path[i + 1].y - path[i].y);
    seglen.push(len);
    total += len;
  }
  if (total < 1e-9) return path[0];
  let dist = Math.min(1, Math.max(0, t)) * total;
  for (let i = 0; i < seglen.length; i++) {
    if (dist <= seglen[i] || i === seglen.length - 1) {
      const u = seglen[i] < 1e-9 ? 0 : dist / seglen[i];
      return {
        x: path[i].x + (path[i + 1].x - path[i].x) * u,
        y: path[i].y + (path[i + 1].y - path[i].y) * u,
      };
    }
    dist -= seglen[i];
  }
  return path[path.length - 1];
}
