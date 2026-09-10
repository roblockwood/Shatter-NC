import React, { useEffect, useMemo, useState } from 'react';
import {
  buildProbeSim3D,
  collectSimPoints,
  motionAxes,
  motionLabel,
  pathCycleDurationMs,
  projectView,
  samplePath,
  type Feature3D,
  type MotionAxisId,
  type Vec3,
} from './probeMotion';
import './ProbeCyclePreview.css';

/** Fixed Blum probe tip Ø 3 mm (site O8717). Do not scale with feature size. */
const PROBE_DIA_MM = 3;
const PROBE_R_MM = PROBE_DIA_MM / 2;
const STEM_LEN = 12;
const ARROW_LEN = 5;

const AXIS_COLOR: Record<MotionAxisId, string> = {
  x: '#ff6666',
  y: '#ffaa00', // amber/yellow — reads as Y in split arrows (triad stays green)
  z: '#6699ff',
};

/** Screen-space radius for a world-space sphere of radius r at point p. */
function screenRadiusAt(p: Vec3, r: number): number {
  const c = projectView(p);
  const e = projectView({ x: p.x + r, y: p.y, z: p.z });
  return Math.hypot(e.x - c.x, e.y - c.y);
}

function featureEdges(f: Feature3D): [Vec3, Vec3][] {
  const edges: [Vec3, Vec3][] = [];
  if (f.kind === 'box') {
    const hx = f.sx / 2;
    const hy = f.sy / 2;
    const hz = f.sz / 2;
    const c = [
      [-hx, -hy, -hz],
      [hx, -hy, -hz],
      [hx, hy, -hz],
      [-hx, hy, -hz],
      [-hx, -hy, hz],
      [hx, -hy, hz],
      [hx, hy, hz],
      [-hx, hy, hz],
    ] as const;
    const idx: [number, number][] = [
      [0, 1],
      [1, 2],
      [2, 3],
      [3, 0],
      [4, 5],
      [5, 6],
      [6, 7],
      [7, 4],
      [0, 4],
      [1, 5],
      [2, 6],
      [3, 7],
    ];
    for (const [a, b] of idx) {
      edges.push([
        { x: f.cx + c[a][0], y: f.cy + c[a][1], z: f.cz + c[a][2] },
        { x: f.cx + c[b][0], y: f.cy + c[b][1], z: f.cz + c[b][2] },
      ]);
    }
  } else if (f.kind === 'cylinder') {
    const n = 16;
    const ring = (z: number) =>
      Array.from({ length: n }, (_, i) => {
        const a = (i / n) * Math.PI * 2;
        return {
          x: f.cx + f.r * Math.cos(a),
          y: f.cy + f.r * Math.sin(a),
          z,
        };
      });
    const bot = ring(f.cz - f.h / 2);
    const top = ring(f.cz + f.h / 2);
    for (let i = 0; i < n; i++) {
      edges.push([bot[i], bot[(i + 1) % n]]);
      edges.push([top[i], top[(i + 1) % n]]);
      if (i % 4 === 0) edges.push([bot[i], top[i]]);
    }
  } else if (f.kind === 'plane') {
    if (f.axis === 'x') {
      edges.push(
        [
          { x: f.at, y: f.u0, z: f.v0 },
          { x: f.at, y: f.u1, z: f.v0 },
        ],
        [
          { x: f.at, y: f.u1, z: f.v0 },
          { x: f.at, y: f.u1, z: f.v1 },
        ],
        [
          { x: f.at, y: f.u1, z: f.v1 },
          { x: f.at, y: f.u0, z: f.v1 },
        ],
        [
          { x: f.at, y: f.u0, z: f.v1 },
          { x: f.at, y: f.u0, z: f.v0 },
        ]
      );
    } else if (f.axis === 'y') {
      edges.push(
        [
          { x: f.u0, y: f.at, z: f.v0 },
          { x: f.u1, y: f.at, z: f.v0 },
        ],
        [
          { x: f.u1, y: f.at, z: f.v0 },
          { x: f.u1, y: f.at, z: f.v1 },
        ],
        [
          { x: f.u1, y: f.at, z: f.v1 },
          { x: f.u0, y: f.at, z: f.v1 },
        ],
        [
          { x: f.u0, y: f.at, z: f.v1 },
          { x: f.u0, y: f.at, z: f.v0 },
        ]
      );
    } else {
      edges.push(
        [
          { x: f.u0, y: f.v0, z: f.at },
          { x: f.u1, y: f.v0, z: f.at },
        ],
        [
          { x: f.u1, y: f.v0, z: f.at },
          { x: f.u1, y: f.v1, z: f.at },
        ],
        [
          { x: f.u1, y: f.v1, z: f.at },
          { x: f.u0, y: f.v1, z: f.at },
        ],
        [
          { x: f.u0, y: f.v1, z: f.at },
          { x: f.u0, y: f.v0, z: f.at },
        ]
      );
    }
  } else if (f.kind === 'walls_x') {
    edges.push(
      [
        { x: f.xNeg, y: f.y0, z: f.z0 },
        { x: f.xNeg, y: f.y1, z: f.z0 },
      ],
      [
        { x: f.xNeg, y: f.y1, z: f.z0 },
        { x: f.xNeg, y: f.y1, z: f.z1 },
      ],
      [
        { x: f.xNeg, y: f.y1, z: f.z1 },
        { x: f.xNeg, y: f.y0, z: f.z1 },
      ],
      [
        { x: f.xNeg, y: f.y0, z: f.z1 },
        { x: f.xNeg, y: f.y0, z: f.z0 },
      ],
      [
        { x: f.xPos, y: f.y0, z: f.z0 },
        { x: f.xPos, y: f.y1, z: f.z0 },
      ],
      [
        { x: f.xPos, y: f.y1, z: f.z0 },
        { x: f.xPos, y: f.y1, z: f.z1 },
      ],
      [
        { x: f.xPos, y: f.y1, z: f.z1 },
        { x: f.xPos, y: f.y0, z: f.z1 },
      ],
      [
        { x: f.xPos, y: f.y0, z: f.z1 },
        { x: f.xPos, y: f.y0, z: f.z0 },
      ]
    );
  } else {
    edges.push(
      [
        { x: f.x0, y: f.yNeg, z: f.z0 },
        { x: f.x1, y: f.yNeg, z: f.z0 },
      ],
      [
        { x: f.x1, y: f.yNeg, z: f.z0 },
        { x: f.x1, y: f.yNeg, z: f.z1 },
      ],
      [
        { x: f.x1, y: f.yNeg, z: f.z1 },
        { x: f.x0, y: f.yNeg, z: f.z1 },
      ],
      [
        { x: f.x0, y: f.yNeg, z: f.z1 },
        { x: f.x0, y: f.yNeg, z: f.z0 },
      ],
      [
        { x: f.x0, y: f.yPos, z: f.z0 },
        { x: f.x1, y: f.yPos, z: f.z0 },
      ],
      [
        { x: f.x1, y: f.yPos, z: f.z0 },
        { x: f.x1, y: f.yPos, z: f.z1 },
      ],
      [
        { x: f.x1, y: f.yPos, z: f.z1 },
        { x: f.x0, y: f.yPos, z: f.z1 },
      ],
      [
        { x: f.x0, y: f.yPos, z: f.z1 },
        { x: f.x0, y: f.yPos, z: f.z0 },
      ]
    );
  }
  return edges;
}

function axisTriad(len = 12): [Vec3, Vec3, string][] {
  return [
    [
      { x: 0, y: 0, z: 0 },
      { x: len, y: 0, z: 0 },
      'X',
    ],
    [
      { x: 0, y: 0, z: 0 },
      { x: 0, y: len, z: 0 },
      'Y',
    ],
    [
      { x: 0, y: 0, z: 0 },
      { x: 0, y: 0, z: len },
      'Z',
    ],
  ];
}

export interface ProbeCyclePreviewProps {
  routineId: string;
  params: Record<string, number>;
  compact?: boolean;
  className?: string;
}

export const ProbeCyclePreview: React.FC<ProbeCyclePreviewProps> = ({
  routineId,
  params,
  compact = false,
  className,
}) => {
  const sim = useMemo(() => buildProbeSim3D(routineId, params), [routineId, params]);

  const [t, setT] = useState(0);
  const [reducedMotion, setReducedMotion] = useState(false);
  const [pulsePhase, setPulsePhase] = useState(0);

  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    const sync = () => setReducedMotion(mq.matches);
    sync();
    mq.addEventListener('change', sync);
    return () => mq.removeEventListener('change', sync);
  }, []);

  const cycleMs = useMemo(() => pathCycleDurationMs(sim.path), [sim.path]);

  useEffect(() => {
    if (reducedMotion || sim.path.length < 2) {
      setT(0.2);
      return;
    }
    let raf = 0;
    const start = performance.now();
    const tick = (now: number) => {
      const elapsed = (now - start) % cycleMs;
      setT(elapsed / cycleMs);
      setPulsePhase(((now - start) % 280) / 280);
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [reducedMotion, sim.path, routineId, cycleMs]);

  const sample = useMemo(
    () => samplePath(sim.path, reducedMotion ? 0.35 : t),
    [sim.path, t, reducedMotion]
  );

  const motion = useMemo(() => motionAxes(sample.dir), [sample.dir]);

  const stem = useMemo(() => {
    const tip = sample.pos;
    const top: Vec3 = { x: tip.x, y: tip.y, z: tip.z + STEM_LEN };
    // Arrow follows true segment direction (combined axes stay diagonal)
    const d = motion.dir;
    const arrowEnd: Vec3 = {
      x: tip.x + d.x * ARROW_LEN,
      y: tip.y + d.y * ARROW_LEN,
      z: tip.z + d.z * ARROW_LEN,
    };
    return { tip, top, arrowEnd };
  }, [sample.pos, motion]);

  const projected = useMemo(() => {
    // Fixed viewBox for this cycle — include stem + tip-arrow envelope at every
    // path waypoint so the camera does not zoom as the stylus animates.
    const world: Vec3[] = collectSimPoints(sim);
    for (const p of sim.path) {
      const top: Vec3 = { x: p.x, y: p.y, z: p.z + STEM_LEN };
      world.push(top);
      // Fixed 3 mm tip footprint so viewBox does not clip the probe
      world.push({ x: p.x + PROBE_R_MM, y: p.y, z: p.z });
      world.push({ x: p.x - PROBE_R_MM, y: p.y, z: p.z });
      world.push({ x: p.x, y: p.y + PROBE_R_MM, z: p.z });
      world.push({ x: p.x, y: p.y - PROBE_R_MM, z: p.z });
      world.push({ x: p.x + ARROW_LEN, y: p.y, z: p.z });
      world.push({ x: p.x - ARROW_LEN, y: p.y, z: p.z });
      world.push({ x: p.x, y: p.y + ARROW_LEN, z: p.z });
      world.push({ x: p.x, y: p.y - ARROW_LEN, z: p.z });
      world.push({ x: p.x, y: p.y, z: p.z + ARROW_LEN });
      world.push({ x: p.x, y: p.y, z: p.z - ARROW_LEN });
    }
    const pts = world.map((p) => projectView(p));
    let minX = Infinity;
    let minY = Infinity;
    let maxX = -Infinity;
    let maxY = -Infinity;
    for (const p of pts) {
      minX = Math.min(minX, p.x);
      minY = Math.min(minY, p.y);
      maxX = Math.max(maxX, p.x);
      maxY = Math.max(maxY, p.y);
    }
    if (!Number.isFinite(minX)) {
      return { minX: -20, minY: -20, w: 40, h: 40 };
    }
    const pad = 8;
    return {
      minX: minX - pad,
      minY: minY - pad,
      w: Math.max(maxX - minX + 2 * pad, 24),
      h: Math.max(maxY - minY + 2 * pad, 24),
    };
  }, [sim]);

  const pathD = useMemo(() => {
    return sim.path
      .map((p, i) => {
        const q = projectView(p);
        return `${i === 0 ? 'M' : 'L'}${q.x.toFixed(2)} ${q.y.toFixed(2)}`;
      })
      .join(' ');
  }, [sim.path]);

  const stylus = projectView(sample.pos);
  const stemTop2 = projectView(stem.top);
  const arrowEnd2 = projectView(stem.arrowEnd);
  const probeR = screenRadiusAt(sample.pos, PROBE_R_MM);
  const pulse =
    sample.onHit && !reducedMotion ? 1 + 0.55 * Math.sin(pulsePhase * Math.PI * 2) : 1;
  const stylusR = probeR * pulse;
  const blipRingR =
    sample.onHit && !reducedMotion
      ? probeR * (2.1 + 1.4 * pulsePhase)
      : stylusR * 2.2;
  const blipRingOpacity =
    sample.onHit && !reducedMotion ? Math.max(0.15, 0.9 * (1 - pulsePhase)) : 0.55;

  // Arrowhead in screen space along projected motion axis (from tip center)
  const arrowHead = useMemo(() => {
    const dx = arrowEnd2.x - stylus.x;
    const dy = arrowEnd2.y - stylus.y;
    const len = Math.hypot(dx, dy) || 1;
    const ux = dx / len;
    const uy = dy / len;
    const hx = -uy;
    const hy = ux;
    const back = 1.8;
    const wing = 1.1;
    return {
      a: {
        x: arrowEnd2.x - ux * back + hx * wing,
        y: arrowEnd2.y - uy * back + hy * wing,
      },
      b: {
        x: arrowEnd2.x - ux * back - hx * wing,
        y: arrowEnd2.y - uy * back - hy * wing,
      },
    };
  }, [arrowEnd2.x, arrowEnd2.y, stylus.x, stylus.y]);

  const hitMarkers = sim.path.filter((p) => p.hit);
  const axisLabel = motionLabel(motion);
  const moving = motion.axes.length > 0;
  const isTool = routineId === 'tool_length';

  const motionColors = motion.axes.map((a) => AXIS_COLOR[a.axis]);
  const shaftMid = {
    x: stylus.x + (arrowEnd2.x - stylus.x) * 0.5,
    y: stylus.y + (arrowEnd2.y - stylus.y) * 0.5,
  };
  const shaftThird = {
    x: stylus.x + (arrowEnd2.x - stylus.x) / 3,
    y: stylus.y + (arrowEnd2.y - stylus.y) / 3,
  };
  const shaftTwoThird = {
    x: stylus.x + ((arrowEnd2.x - stylus.x) * 2) / 3,
    y: stylus.y + ((arrowEnd2.y - stylus.y) * 2) / 3,
  };

  // End-mill body in world space (tip at contact, shank along +Z)
  const toolGeom = useMemo(() => {
    if (!isTool) return null;
    const tip = sample.pos;
    const r = 2.2;
    const shankTop = STEM_LEN;
    const bodyH = STEM_LEN * 0.45;
    const corners = (z: number, rad: number): Vec3[] => {
      const pts: Vec3[] = [];
      for (let i = 0; i < 6; i++) {
        const a = (i / 6) * Math.PI * 2;
        pts.push({
          x: tip.x + rad * Math.cos(a),
          y: tip.y + rad * Math.sin(a),
          z: tip.z + z,
        });
      }
      return pts;
    };
    return {
      tip,
      tipRing: corners(0.3, r * 0.55),
      bodyBot: corners(1.2, r),
      bodyTop: corners(1.2 + bodyH, r),
      shankBot: corners(1.2 + bodyH, r * 0.7),
      shankTopRing: corners(shankTop, r * 0.7),
      axisTop: { x: tip.x, y: tip.y, z: tip.z + shankTop } as Vec3,
    };
  }, [isTool, sample.pos]);

  return (
    <div
      className={`probe-cycle-preview${compact ? ' probe-cycle-preview--compact' : ''}${className ? ` ${className}` : ''}`}
    >
      <div className="probe-cycle-preview-title">
        CYCLE PREVIEW (ISO)
        {sample.onHit ? ' · HIT' : moving ? ` · ${axisLabel}` : ''}
        {isTool ? ' · TOOL' : ''}
      </div>
      <svg
        className="probe-cycle-preview-svg"
        viewBox={`${projected.minX} ${projected.minY} ${projected.w} ${projected.h}`}
        preserveAspectRatio="xMidYMid meet"
        role="img"
        aria-label={
          isTool
            ? 'Isometric tool-length measure schematic'
            : 'Isometric probe cycle schematic from Blum helper motion'
        }
      >
        {axisTriad(Math.max(projected.w, projected.h) * 0.12).map(([a, b, label], i) => {
          const pa = projectView(a);
          const pb = projectView(b);
          return (
            <g key={`ax${i}`}>
              <line
                x1={pa.x}
                y1={pa.y}
                x2={pb.x}
                y2={pb.y}
                className={`probe-preview-axis probe-preview-axis--${label.toLowerCase()}`}
              />
              <text x={pb.x} y={pb.y} className="probe-preview-label">
                {label}
              </text>
            </g>
          );
        })}

        {sim.features.flatMap((f, fi) => {
          const isClearance = f.kind === 'plane' && f.reference;
          return featureEdges(f).map(([a, b], ei) => {
            const pa = projectView(a);
            const pb = projectView(b);
            return (
              <line
                key={`fe${fi}-${ei}`}
                x1={pa.x}
                y1={pa.y}
                x2={pb.x}
                y2={pb.y}
                className={
                  isClearance ? 'probe-preview-clearance' : 'probe-preview-feature'
                }
              />
            );
          });
        })}

        {pathD && <path d={pathD} className="probe-preview-path" />}

        {hitMarkers.map((h, i) => {
          const p = projectView(h);
          return (
            <circle
              key={`hit${i}`}
              cx={p.x}
              cy={p.y}
              r={probeR * 0.85}
              className="probe-preview-hit-mark"
            />
          );
        })}

        {/* Feature tags only — skip axis-letter labels (triad + title already cover axes) */}
        {sim.labels
          .filter((lab) => !/^[XYZ]+$/i.test(lab.text.trim()))
          .map((lab, i) => {
            const p = projectView(lab.at);
            return (
              <text key={`l${i}`} x={p.x} y={p.y} className="probe-preview-label">
                {lab.text}
              </text>
            );
          })}

        {moving && (
          <g className="probe-preview-motion">
            {motionColors.length === 1 && (
              <line
                x1={stylus.x}
                y1={stylus.y}
                x2={arrowEnd2.x}
                y2={arrowEnd2.y}
                className="probe-preview-motion-shaft"
                stroke={motionColors[0]}
              />
            )}
            {motionColors.length === 2 && (
              <>
                <line
                  x1={stylus.x}
                  y1={stylus.y}
                  x2={shaftMid.x}
                  y2={shaftMid.y}
                  className="probe-preview-motion-shaft"
                  stroke={motionColors[0]}
                />
                <line
                  x1={shaftMid.x}
                  y1={shaftMid.y}
                  x2={arrowEnd2.x}
                  y2={arrowEnd2.y}
                  className="probe-preview-motion-shaft"
                  stroke={motionColors[1]}
                />
              </>
            )}
            {motionColors.length >= 3 && (
              <>
                <line
                  x1={stylus.x}
                  y1={stylus.y}
                  x2={shaftThird.x}
                  y2={shaftThird.y}
                  className="probe-preview-motion-shaft"
                  stroke={motionColors[0]}
                />
                <line
                  x1={shaftThird.x}
                  y1={shaftThird.y}
                  x2={shaftTwoThird.x}
                  y2={shaftTwoThird.y}
                  className="probe-preview-motion-shaft"
                  stroke={motionColors[1]}
                />
                <line
                  x1={shaftTwoThird.x}
                  y1={shaftTwoThird.y}
                  x2={arrowEnd2.x}
                  y2={arrowEnd2.y}
                  className="probe-preview-motion-shaft"
                  stroke={motionColors[2]}
                />
              </>
            )}
            <polygon
              points={`${arrowEnd2.x},${arrowEnd2.y} ${arrowHead.a.x},${arrowHead.a.y} ${arrowHead.b.x},${arrowHead.b.y}`}
              className="probe-preview-motion-head"
              fill={motionColors[motionColors.length - 1]}
              stroke={motionColors[motionColors.length - 1]}
            />
          </g>
        )}

        {isTool && toolGeom ? (
          <g
            className={`probe-preview-tool${sample.onHit ? ' probe-preview-tool--hit' : ''}`}
          >
            {/* fluted body + shank wireframe */}
            {toolGeom.bodyBot.map((p, i) => {
              const a = projectView(p);
              const b = projectView(toolGeom.bodyBot[(i + 1) % toolGeom.bodyBot.length]);
              return (
                <line
                  key={`tb${i}`}
                  x1={a.x}
                  y1={a.y}
                  x2={b.x}
                  y2={b.y}
                  className="probe-preview-tool-edge"
                />
              );
            })}
            {toolGeom.bodyTop.map((p, i) => {
              const a = projectView(p);
              const b = projectView(toolGeom.bodyTop[(i + 1) % toolGeom.bodyTop.length]);
              const c = projectView(toolGeom.bodyBot[i]);
              return (
                <g key={`tt${i}`}>
                  <line
                    x1={a.x}
                    y1={a.y}
                    x2={b.x}
                    y2={b.y}
                    className="probe-preview-tool-edge"
                  />
                  <line
                    x1={a.x}
                    y1={a.y}
                    x2={c.x}
                    y2={c.y}
                    className="probe-preview-tool-edge"
                  />
                </g>
              );
            })}
            {toolGeom.shankTopRing.map((p, i) => {
              const a = projectView(p);
              const b = projectView(
                toolGeom.shankTopRing[(i + 1) % toolGeom.shankTopRing.length]
              );
              const c = projectView(toolGeom.shankBot[i]);
              return (
                <g key={`ts${i}`}>
                  <line
                    x1={a.x}
                    y1={a.y}
                    x2={b.x}
                    y2={b.y}
                    className="probe-preview-tool-shank"
                  />
                  <line
                    x1={a.x}
                    y1={a.y}
                    x2={c.x}
                    y2={c.y}
                    className="probe-preview-tool-shank"
                  />
                </g>
              );
            })}
            {/* tip flat */}
            {toolGeom.tipRing.map((p, i) => {
              const a = projectView(p);
              const b = projectView(toolGeom.tipRing[(i + 1) % toolGeom.tipRing.length]);
              return (
                <line
                  key={`tip${i}`}
                  x1={a.x}
                  y1={a.y}
                  x2={b.x}
                  y2={b.y}
                  className="probe-preview-tool-tip"
                />
              );
            })}
            <circle
              cx={stylus.x}
              cy={stylus.y}
              r={stylusR * 0.85}
              className={`probe-preview-tool-contact${sample.onHit ? ' probe-preview-stylus--hit' : ''}`}
            />
            {sample.onHit && (
              <circle
                cx={stylus.x}
                cy={stylus.y}
                r={blipRingR}
                className="probe-preview-stylus-ring"
                opacity={blipRingOpacity}
              />
            )}
          </g>
        ) : (
          <>
            {/* Probe stem (+Z); motion arrow drawn under tip above */}
            <line
              x1={stylus.x}
              y1={stylus.y}
              x2={stemTop2.x}
              y2={stemTop2.y}
              className="probe-preview-stem"
            />
            <circle
              cx={stylus.x}
              cy={stylus.y}
              r={stylusR}
              className={`probe-preview-stylus${sample.onHit ? ' probe-preview-stylus--hit' : ''}`}
            />
            {sample.onHit && (
              <circle
                cx={stylus.x}
                cy={stylus.y}
                r={blipRingR}
                className="probe-preview-stylus-ring"
                opacity={blipRingOpacity}
              />
            )}
          </>
        )}
      </svg>
    </div>
  );
};
