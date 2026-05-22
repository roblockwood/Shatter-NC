import React, { useMemo } from 'react';
import {
  STATUS_COLORS,
  STATUS_LABELS,
  STATUS_ORDER,
  formatDuration,
  timeRangeDisplayLabel,
  type StatusDurationSlice,
  type TimeRange,
} from '../../utils/statusTimelineUtils';
import './StatusPieChart.css';

interface StatusPieChartProps {
  slices: StatusDurationSlice[];
  timeRange: TimeRange;
  loading?: boolean;
}

const CX = 50;
const CY = 50;
const OUTER_R = 42;
const INNER_R = 26;

function polarToCartesian(cx: number, cy: number, r: number, angleDeg: number) {
  const angleRad = ((angleDeg - 90) * Math.PI) / 180;
  return {
    x: cx + r * Math.cos(angleRad),
    y: cy + r * Math.sin(angleRad),
  };
}

function describeDonutSlice(
  startAngle: number,
  endAngle: number,
  outerR: number,
  innerR: number
): string {
  if (endAngle - startAngle >= 360) {
    endAngle = startAngle + 359.999;
  }
  const outerStart = polarToCartesian(CX, CY, outerR, startAngle);
  const outerEnd = polarToCartesian(CX, CY, outerR, endAngle);
  const innerEnd = polarToCartesian(CX, CY, innerR, endAngle);
  const innerStart = polarToCartesian(CX, CY, innerR, startAngle);
  const largeArc = endAngle - startAngle > 180 ? 1 : 0;

  return [
    `M ${outerStart.x} ${outerStart.y}`,
    `A ${outerR} ${outerR} 0 ${largeArc} 1 ${outerEnd.x} ${outerEnd.y}`,
    `L ${innerEnd.x} ${innerEnd.y}`,
    `A ${innerR} ${innerR} 0 ${largeArc} 0 ${innerStart.x} ${innerStart.y}`,
    'Z',
  ].join(' ');
}

export const StatusPieChart: React.FC<StatusPieChartProps> = ({
  slices,
  timeRange,
  loading = false,
}) => {
  const arcs = useMemo(() => {
    const withDuration = slices.filter((s) => s.ms > 0);
    const totalMs = withDuration.reduce((sum, s) => sum + s.ms, 0);
    if (totalMs === 0) return [];

    let angle = 0;
    return withDuration.map((slice) => {
      const sweep = (slice.ms / totalMs) * 360;
      const startAngle = angle;
      const endAngle = angle + sweep;
      angle = endAngle;
      return {
        ...slice,
        path: describeDonutSlice(startAngle, endAngle, OUTER_R, INNER_R),
        color: STATUS_COLORS[slice.status],
      };
    });
  }, [slices]);

  const hasData = arcs.length > 0;

  if (loading) {
    return <div className="status-pie-chart timeline-loading">LOADING...</div>;
  }

  if (!hasData) {
    return <div className="status-pie-chart timeline-empty">NO STATUS DATA</div>;
  }

  return (
    <div className="status-pie-chart">
      <div className="status-pie-chart-visual">
        <svg
          className="status-pie-svg"
          viewBox="0 0 100 100"
          aria-label={`Status distribution for ${timeRangeDisplayLabel(timeRange)}`}
        >
          {arcs.map((arc) => (
            <path
              key={arc.status}
              d={arc.path}
              fill={arc.color}
              stroke="var(--color-bg-surface)"
              strokeWidth="0.8"
              className="status-pie-slice"
              style={{ filter: `drop-shadow(0 0 3px ${arc.color})` }}
            />
          ))}
          <text
            x={CX}
            y={CY}
            textAnchor="middle"
            dominantBaseline="middle"
            className="status-pie-center-label"
          >
            {timeRangeDisplayLabel(timeRange)}
          </text>
        </svg>
      </div>
      <div className="status-pie-legend">
        {STATUS_ORDER.map((status) => {
          const slice = slices.find((s) => s.status === status);
          const ms = slice?.ms ?? 0;
          const percent = slice?.percent ?? 0;
          return (
            <div key={status} className="status-pie-legend-row">
              <span
                className="status-pie-swatch"
                style={{ backgroundColor: STATUS_COLORS[status] }}
                aria-hidden
              />
              <span className="status-pie-legend-label">{STATUS_LABELS[status]}</span>
              <span className="status-pie-legend-percent">
                {percent.toFixed(1)}%
              </span>
              <span className="status-pie-legend-duration">
                ({formatDuration(ms)})
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
