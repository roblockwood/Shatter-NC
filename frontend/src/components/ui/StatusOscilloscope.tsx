import React, { useEffect, useRef, useState } from 'react';
import type { StatusEvent } from '../../api/summary';
import { useLocalChartTimeAxisMode } from '../../hooks/useLocalChartTimeAxisMode';
import {
  buildOscilloscopeAxisDivisionLabels,
  getOscilloscopeTicksForMode,
  oscilloscopeAxisEndLabels,
} from '../../utils/chartTimeAxis';
import { ChartTimeAxisToggle } from './ChartTimeAxisToggle';
import './StatusOscilloscope.css';

interface StatusOscilloscopeProps {
  statusHistory: StatusEvent[];
  currentStatus?: string;
  timeRange: '1h' | '8h' | '24h' | '7d';
  compact?: boolean;
  /** CNC (default) vs Kaeser compressor (infer_status-style strings). */
  variant?: 'cnc' | 'compressor';
  /** When variant=compressor, false forces bottom band (offline) for live endpoint. */
  isOnline?: boolean;
  /** Grow with parent flex layout instead of fixed 120px (e.g. compressor status timeline pane). */
  fillHeight?: boolean;
  /** Unique key for persisting this chart’s relative vs clock axis mode. */
  timeAxisStorageKey: string;
}

// CNC: Operating (top) … Error (bottom)
const CNC_STATUS_LEVELS: { [key: string]: number } = {
  operating: 3,
  standby: 2,
  stopped: 1,
  error: 0,
};

const CNC_STATUS_LABELS = ['OPERATING', 'STANDBY', 'STOPPED', 'ERROR'];

// Compressor: load (top) … offline (bottom); error sits above offline — aligns with infer_status + HMI text
const COMPRESSOR_STATUS_LEVELS: { [key: string]: number } = {
  load: 4,
  idle: 3,
  back_pressure: 3,
  online: 3,
  stopped: 2,
  error: 1,
  offline: 0,
  unknown: 0,
};

const COMPRESSOR_STATUS_LABELS = ['LOAD', 'IDLE', 'STOPPED', 'ERROR', 'OFFLINE'];

const normalizeCncStatus = (status: string | undefined, _isOnline?: boolean): string => {
  if (!status) return 'standby';
  const lower = status.toLowerCase().trim();

  if (lower === 'operating' || lower.includes('operating') || lower.includes('running')) return 'operating';
  if (lower === 'standby' || lower.includes('standby') || lower.includes('idle')) return 'standby';
  if (lower === 'stopped' || lower.includes('stopped')) return 'stopped';
  if (lower === 'error' || lower.includes('error') || lower.includes('occurred')) return 'error';

  return 'standby';
};

const normalizeCompressorStatus = (status: string | undefined, isOnline?: boolean): string => {
  if (isOnline === false) return 'offline';
  if (!status) return 'unknown';
  const lower = status.toLowerCase().trim();

  if (
    lower.includes('error') ||
    lower.includes('fault') ||
    lower.includes('alarm') ||
    lower.includes('trip') ||
    lower.includes('stör') ||
    lower.includes('stoer')
  ) {
    return 'error';
  }

  if (lower === 'load' || lower.includes('on_load') || lower.includes('on load')) return 'load';
  if (lower.includes('no_load') || lower.includes('no load') || lower.includes('unload')) return 'idle';
  if (lower.includes('running') || lower.includes('operating') || lower.includes('production'))
    return 'load';
  if (lower.includes('load') && !lower.includes('download') && !lower.includes('unload')) return 'load';
  if (lower === 'idle' || lower.includes('idle')) return 'idle';
  if (lower.includes('back_pressure') || lower.includes('back pressure')) return 'back_pressure';
  if (lower === 'online' || lower === 'on') return 'online';
  if (lower === 'stopped' || lower.includes('stopped')) return 'stopped';
  if (lower === 'offline' || lower === 'unknown' || lower.includes('unknown')) return 'unknown';

  // Unknown slug from backend (e.g. automatic_operation) — not "idle"
  return 'online';
};

export const StatusOscilloscope: React.FC<StatusOscilloscopeProps> = ({
  statusHistory,
  currentStatus,
  timeRange,
  compact = false,
  variant = 'cnc',
  isOnline,
  fillHeight = false,
  timeAxisStorageKey,
}) => {
  const { timeAxisMode, toggleTimeAxisMode } = useLocalChartTimeAxisMode(timeAxisStorageKey);
  const norm =
    variant === 'compressor' ? normalizeCompressorStatus : normalizeCncStatus;
  const STATUS_LEVELS =
    variant === 'compressor' ? COMPRESSOR_STATUS_LEVELS : CNC_STATUS_LEVELS;
  const STATUS_LABELS =
    variant === 'compressor' ? COMPRESSOR_STATUS_LABELS : CNC_STATUS_LABELS;
  const [oscilloscopeWidth, setOscilloscopeWidth] = useState(800);
  const [scaleX, setScaleX] = useState(1);
  const [hoveredPoint, setHoveredPoint] = useState<{ x: number; y: number; status: string; timestamp: Date } | null>(null);
  const [tooltipPosition, setTooltipPosition] = useState<{ x: number; y: number } | null>(null);
  const oscilloscopeRef = useRef<HTMLDivElement>(null);
  const oscilloscopeDataRef = useRef<HTMLDivElement>(null);

  // Calculate time range
  const endTime = new Date();
  const startTime = new Date();
  switch (timeRange) {
    case '1h':
      startTime.setHours(startTime.getHours() - 1);
      break;
    case '8h':
      startTime.setHours(startTime.getHours() - 8);
      break;
    case '24h':
      startTime.setHours(startTime.getHours() - 24);
      break;
    case '7d':
      startTime.setDate(startTime.getDate() - 7);
      break;
  }
  const totalDuration = endTime.getTime() - startTime.getTime();

  // Build oscilloscope data points
  const buildOscilloscopeData = () => {
    const dataPoints: Array<{ time: number; level: number; status: string }> = [];
    
    const defaultLive =
      variant === 'compressor' ? 'unknown' : 'standby';

    // No samples: only draw a flat span when we have live context (same as Brother StatusTimeline).
    if (statusHistory.length === 0) {
      const hasLiveData = currentStatus !== undefined || isOnline !== undefined;
      if (!hasLiveData) {
        return dataPoints;
      }
      const normalized = norm(currentStatus || defaultLive, isOnline);
      const level = STATUS_LEVELS[normalized] ?? (variant === 'compressor' ? 0 : 2);
      dataPoints.push({ time: 0, level, status: normalized });
      dataPoints.push({ time: 100, level, status: normalized });
      return dataPoints;
    }

    const sortedEvents = [...statusHistory].sort((a, b) => 
      new Date(a.time).getTime() - new Date(b.time).getTime()
    );

    // Do not add a synthetic point at time 0. A left-edge segment tied to currentStatus would
    // jump on every load/idle flip; we only plot actual samples (StatusTimeline pattern).

    for (const event of sortedEvents) {
      const eventTime = new Date(event.time).getTime();
      if (eventTime >= startTime.getTime() && eventTime <= endTime.getTime()) {
        const normalized = norm(event.status);
        const relativeTime = ((eventTime - startTime.getTime()) / totalDuration) * 100;
        dataPoints.push({
          time: relativeTime,
          level: STATUS_LEVELS[normalized] ?? (variant === 'compressor' ? 3 : 2),
          status: normalized,
        });
      }
    }

    // Extend to "now" only when live status is known — avoids inventing a tail from last sample.
    if (currentStatus !== undefined) {
      const normalized = norm(currentStatus, isOnline);
      dataPoints.push({
        time: 100,
        level: STATUS_LEVELS[normalized] ?? (variant === 'compressor' ? 0 : 2),
        status: normalized,
      });
    }

    return dataPoints;
  };

  const oscilloscopeData = buildOscilloscopeData();

  const timeTicks = getOscilloscopeTicksForMode(timeRange, startTime, endTime, timeAxisMode);
  const timeDivisions = buildOscilloscopeAxisDivisionLabels(
    timeRange,
    timeTicks,
    endTime,
    timeAxisMode
  );
  const axisEnds = oscilloscopeAxisEndLabels(timeRange, startTime, endTime, timeAxisMode);

  // Dynamic width calculation - match PollingOscilloscope approach
  useEffect(() => {
    const updateWidth = () => {
      if (oscilloscopeRef.current && oscilloscopeDataRef.current) {
        // Get the actual available width from the container
        const container = oscilloscopeRef.current;
        const containerWidth = container.offsetWidth;
        
        // In compact mode, use a much larger data width to fill the space
        // This creates a wider oscilloscope that gets compressed to fit
        if (compact) {
          // Use a wide data width (e.g., 800px) so it fills the available space
          // The scale will compress it to fit the container
          const dataWidth = 800;
          setOscilloscopeWidth(dataWidth);
          
          if (containerWidth > 0 && dataWidth > 0) {
            // Scale to fit container - compresses the wide data to fit
            setScaleX(containerWidth / dataWidth);
          } else {
            setScaleX(1);
          }
        } else {
          // In full mode, use a much larger data width to fill the space
          // This creates a wider oscilloscope that gets compressed to fit
          const dataWidth = 2000;
          setOscilloscopeWidth(dataWidth);
          
          if (containerWidth > 0 && dataWidth > 0) {
            // Scale to fit container - compresses the wide data to fit
            setScaleX(containerWidth / dataWidth);
          } else {
            setScaleX(1);
          }
        }
      }
    };

    updateWidth();
    const resizeObserver = new ResizeObserver(updateWidth);
    if (oscilloscopeRef.current) {
      resizeObserver.observe(oscilloscopeRef.current);
    }

    return () => resizeObserver.disconnect();
  }, [compact, fillHeight]);

  // Generate SVG oscilloscope
  const renderOscilloscope = () => {
    const maxStatusLevel = variant === 'compressor' ? 4 : 3;
    const statusBandCount = maxStatusLevel + 1;
    const gridLevels = Array.from({ length: statusBandCount }, (_, i) => maxStatusLevel - i);

    // Convert data points to SVG coordinates (as percentages like PollingOscilloscope)
    const svgPoints: Array<{ x: number; y: number; status: string; timestamp: Date }> = [];
    
    if (oscilloscopeData.length > 0) {
      oscilloscopeData.forEach((point, idx) => {
        const x = point.time; // Already a percentage (0-100)
        const levelY = (1 - point.level / maxStatusLevel) * 100;
        const paddedY = 8 + (levelY / 100) * 84; // Map to 8-92 range
        const rowHeight = 84 / statusBandCount;
        const rowCenter = paddedY;
        // Tight oscillation
        const oscillation = Math.sin(x * 2.5) * (rowHeight * 0.12);
        const y = Math.max(rowCenter - rowHeight/2 + 1, Math.min(rowCenter + rowHeight/2 - 1, rowCenter + oscillation));
        
        const timestamp = new Date(startTime.getTime() + (point.time / 100) * totalDuration);
        svgPoints.push({ x, y, status: point.status, timestamp });
        
        // Add intermediate points for smoother transitions
        if (idx < oscilloscopeData.length - 1) {
          const nextPoint = oscilloscopeData[idx + 1];
          const nextX = nextPoint.time; // Already a percentage
          const nextLevelY = (1 - nextPoint.level / maxStatusLevel) * 100;
          const nextPaddedY = 8 + (nextLevelY / 100) * 84;
          
          if (Math.abs(point.level - nextPoint.level) > 0.1) {
            const steps = 3;
            for (let i = 1; i < steps; i++) {
              const t = i / steps;
              const interpX = x + (nextX - x) * t;
              const interpY = rowCenter + (nextPaddedY - rowCenter) * t;
              const interpOscillation = Math.sin(interpX * 2.5) * (rowHeight * 0.12);
              const finalY = Math.max(interpY - rowHeight/2 + 1, Math.min(interpY + rowHeight/2 - 1, interpY + interpOscillation));
              svgPoints.push({ 
                x: interpX, 
                y: finalY, 
                status: point.status, 
                timestamp: new Date(startTime.getTime() + (interpX / 100) * totalDuration) 
              });
            }
          }
        }
      });
    }

    // Same path as Brother StatusTimeline: Q through midpoint then smooth T to next point
    const buildPath = () => {
      if (svgPoints.length === 0) return '';

      let path = `M ${svgPoints[0].x},${svgPoints[0].y}`;
      for (let i = 1; i < svgPoints.length; i++) {
        const prev = svgPoints[i - 1];
        const curr = svgPoints[i];
        const midX = (prev.x + curr.x) / 2;
        const midY = (prev.y + curr.y) / 2;
        path += ` Q ${prev.x},${prev.y} ${midX},${midY} T ${curr.x},${curr.y}`;
      }
      return path;
    };

    const pathData = buildPath();

    if (compact) {
      // Compact mode - simple SVG without labels
      return (
        <div 
          ref={oscilloscopeDataRef}
          className="status-oscilloscope-display-wrapper"
          style={{
            transform: `scaleX(${scaleX})`,
            transformOrigin: 'left center',
            width: `${oscilloscopeWidth}px`,
            maxWidth: 'none',
            boxSizing: 'border-box',
            willChange: 'auto',
            backfaceVisibility: 'hidden',
          }}
        >
          <svg
            className="status-oscilloscope-svg"
            width="100%"
            height="100%"
            viewBox="0 0 100 100"
            preserveAspectRatio="none"
            shapeRendering="crispEdges"
            style={{ 
              imageRendering: 'crisp-edges' as const,
              filter: 'none',
            }}
          >
            {/* Grid lines for each status level */}
            {gridLevels.map((level) => {
              const y = 8 + ((1 - level / maxStatusLevel) * 84);
              return (
                <line
                  key={`grid-${level}`}
                  x1="0"
                  y1={y}
                  x2="100"
                  y2={y}
                  stroke="var(--color-text-dim)"
                  strokeWidth="0.5"
                  opacity="0.3"
                  vectorEffect="non-scaling-stroke"
                  shapeRendering="crispEdges"
                  style={{ filter: 'none' }}
                />
              );
            })}

            {/* Oscilloscope trace — match Brother StatusTimeline (strokeWidth 2, non-scaling) */}
            <path
              d={pathData}
              fill="none"
              stroke="var(--color-text-primary)"
              strokeWidth="2"
              strokeLinecap="butt"
              strokeLinejoin="miter"
              className="status-oscilloscope-trace"
              vectorEffect="non-scaling-stroke"
              shapeRendering="crispEdges"
              style={{ filter: 'none' }}
            />
          </svg>
        </div>
      );
    }

    // Full mode - with labels, tooltips, time divisions
    return (
      <div className="status-oscilloscope-full-wrapper">
        <div className="status-oscilloscope-grid">
          {/* Y-axis labels */}
          <div className="status-oscilloscope-labels-column">
            {STATUS_LABELS.map((label, idx) => (
              <div key={idx} className="status-oscilloscope-row">
                <span className="status-oscilloscope-y-label">
                  {label.padEnd(8)}
                </span>
                <span className="status-oscilloscope-line">│</span>
              </div>
            ))}
          </div>
          {/* SVG oscilloscope */}
          <div 
            className="status-oscilloscope-svg-container" 
            ref={oscilloscopeDataRef}
          >
            <div
              style={{
                transform: `scaleX(${scaleX})`,
                transformOrigin: 'left center',
                width: `${oscilloscopeWidth}px`,
                maxWidth: 'none',
                height: '100%',
                boxSizing: 'border-box',
                willChange: 'auto',
                backfaceVisibility: 'hidden',
              }}
            >
              <svg
                className="status-oscilloscope-svg"
                width="100%"
                height="100%"
                viewBox="0 0 100 100"
                preserveAspectRatio="none"
                shapeRendering="crispEdges"
                style={{ 
                  imageRendering: 'crisp-edges' as const,
                  filter: 'none',
                }}
              >
              {/* Grid lines for each status level */}
              {gridLevels.map((level) => {
                const levelY = (1 - level / maxStatusLevel) * 100;
                const paddedY = 8 + (levelY / 100) * 84;
                return (
                  <line
                    key={`grid-${level}`}
                    x1="0"
                    y1={paddedY}
                    x2="100"
                    y2={paddedY}
                    stroke="var(--color-text-dim)"
                    strokeWidth="0.5"
                    opacity="0.3"
                    vectorEffect="non-scaling-stroke"
                    shapeRendering="crispEdges"
                    style={{ filter: 'none' }}
                  />
                );
              })}

              {/* Time division markers */}
              {timeDivisions.map((div) => (
                <line
                  key={`time-div-${div.x}-${div.label}`}
                  x1={div.x}
                  y1="0"
                  x2={div.x}
                  y2="100"
                  stroke="var(--color-text-dim)"
                  strokeWidth="0.3"
                  strokeDasharray="1 1"
                  opacity="0.2"
                  shapeRendering="crispEdges"
                  className="status-oscilloscope-time-division"
                  style={{ filter: 'none' }}
                />
              ))}

              {/* Oscilloscope trace — match Brother StatusTimeline (strokeWidth 2, non-scaling) */}
              <path
                d={pathData}
                fill="none"
                stroke="var(--color-text-primary)"
                strokeWidth="2"
                strokeLinecap="butt"
                strokeLinejoin="miter"
                className="status-oscilloscope-trace"
                vectorEffect="non-scaling-stroke"
                shapeRendering="crispEdges"
                style={{ filter: 'none' }}
              />

              {/* Timestamp markers with hover */}
              {oscilloscopeData.map((dataPoint, dataIdx) => {
                const x = dataPoint.time;
                const timestamp = new Date(startTime.getTime() + (dataPoint.time / 100) * totalDuration);
                const hoverRadius = 0.5;
                const levelY = (1 - dataPoint.level / maxStatusLevel) * 100;
                const paddedY = 8 + (levelY / 100) * 84;
                
                return (
                  <g key={dataIdx}>
                    {/* Invisible wider rectangle for easier hover */}
                    <rect
                      x={x - hoverRadius}
                      y="0"
                      width={hoverRadius * 2}
                      height="100"
                      fill="transparent"
                      className="status-oscilloscope-timestamp-hover-area"
                      onMouseEnter={(e) => {
                        const rect = e.currentTarget.getBoundingClientRect();
                        const containerRect = e.currentTarget.closest('.status-oscilloscope-full-wrapper')?.getBoundingClientRect();
                        if (containerRect) {
                          const normalized = norm(dataPoint.status);
                          setHoveredPoint({
                            x: x,
                            y: paddedY,
                            status: normalized.toUpperCase(),
                            timestamp: timestamp,
                          });
                          
                          const tooltipWidth = 150;
                          const tooltipHeight = 40;
                          const pointX = rect.left - containerRect.left + rect.width / 2;
                          const pointY = rect.top - containerRect.top;
                          
                          let tooltipX = pointX;
                          const minX = tooltipWidth / 2;
                          const maxX = containerRect.width - tooltipWidth / 2;
                          tooltipX = Math.max(minX, Math.min(maxX, tooltipX));
                          
                          let tooltipY = pointY - tooltipHeight - 5;
                          if (tooltipY < 0) {
                            tooltipY = pointY + rect.height + 5;
                          }
                          
                          setTooltipPosition({
                            x: tooltipX,
                            y: tooltipY,
                          });
                        }
                      }}
                      onMouseLeave={() => {
                        setHoveredPoint(null);
                        setTooltipPosition(null);
                      }}
                    />
                    {/* Visible line */}
                    <line
                      x1={x}
                      y1="0"
                      x2={x}
                      y2="100"
                      stroke="var(--color-text-primary)"
                      strokeWidth="0.5"
                      strokeDasharray="3 2"
                      opacity="0.25"
                      shapeRendering="crispEdges"
                      className="status-oscilloscope-timestamp-line"
                      pointerEvents="none"
                      style={{ filter: 'none' }}
                    />
                  </g>
                );
              })}
              </svg>
            </div>
          </div>
        </div>
        {/* Tooltip */}
        {hoveredPoint && tooltipPosition && (
          <div 
            className="status-oscilloscope-tooltip"
            style={{
              left: `${tooltipPosition.x}px`,
              top: `${tooltipPosition.y}px`,
            }}
          >
            {hoveredPoint.status}<br/>
            {hoveredPoint.timestamp.toLocaleString()}
          </div>
        )}
        {/* X-axis labels */}
        <div className="status-oscilloscope-x-axis">
          <span className="status-oscilloscope-x-label-start">{axisEnds.left}</span>
          <div className="status-oscilloscope-x-divisions">
            {timeDivisions.map((div, divIdx) => {
              // Skip first and last (PAST and NOW are already shown)
              if (divIdx === 0 || divIdx === timeDivisions.length - 1) return null;
              return (
                <span
                  key={`time-label-${divIdx}-${div.label}`}
                  className="status-oscilloscope-x-label-division"
                  style={{ left: `${div.x}%`, transform: 'translateX(-50%)' }}
                >
                  {div.label}
                </span>
              );
            })}
          </div>
          <div className="status-oscilloscope-x-axis-endgroup">
            <span className="status-oscilloscope-x-label-end">{axisEnds.right}</span>
            <ChartTimeAxisToggle
              timeAxisMode={timeAxisMode}
              toggleTimeAxisMode={toggleTimeAxisMode}
            />
          </div>
        </div>
      </div>
    );
  };

  const svgHeight = compact ? 40 : 120;
  const useFillHeight = fillHeight && !compact;

  return (
    <div 
      className={`status-oscilloscope ${compact ? 'status-oscilloscope-compact' : 'status-oscilloscope-full'}${useFillHeight ? ' status-oscilloscope--fill-height' : ''}`}
      ref={oscilloscopeRef}
      style={{ width: '100%', maxWidth: '100%', overflow: 'hidden', boxSizing: 'border-box' }}
    >
      <div 
        className="status-oscilloscope-display"
        style={{ 
          ...(useFillHeight
            ? { flex: 1, minHeight: 0, height: '100%' }
            : { height: `${svgHeight}px` }),
          width: '100%',
          maxWidth: '100%',
          overflow: 'hidden',
          boxSizing: 'border-box',
        }}
      >
        {renderOscilloscope()}
      </div>
    </div>
  );
};
