import React, { useEffect, useRef, useState } from 'react';
import type { StatusEvent } from '../../api/summary';
import './StatusOscilloscope.css';

interface StatusOscilloscopeProps {
  statusHistory: StatusEvent[];
  currentStatus?: string;
  timeRange: '1h' | '8h' | '24h' | '7d';
  compact?: boolean;
}

// Status mapping for Y-axis (4 states: operating, standby, stopped, error)
// Order: Operating (top), Standby, Stopped, Error (bottom)
const STATUS_LEVELS: { [key: string]: number } = {
  'operating': 3,
  'standby': 2,
  'stopped': 1,
  'error': 0,
};

const STATUS_LABELS = ['OPERATING', 'STANDBY', 'STOPPED', 'ERROR'];

// Normalize status string to one of the 4 states (exclude 'off')
const normalizeStatus = (status: string | undefined): string => {
  if (!status) return 'standby';
  const lower = status.toLowerCase().trim();
  
  // Map to actual machine statuses (exclude 'off')
  if (lower === 'operating' || lower.includes('operating') || lower.includes('running')) return 'operating';
  if (lower === 'standby' || lower.includes('standby') || lower.includes('idle')) return 'standby';
  if (lower === 'stopped' || lower.includes('stopped')) return 'stopped';
  if (lower === 'error' || lower.includes('error') || lower.includes('occurred')) return 'error';
  
  // Default to standby
  return 'standby';
};

export const StatusOscilloscope: React.FC<StatusOscilloscopeProps> = ({
  statusHistory,
  currentStatus,
  timeRange,
  compact = false,
}) => {
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
    
    // If no events, use current status
    if (statusHistory.length === 0) {
      const normalized = normalizeStatus(currentStatus || 'standby');
      dataPoints.push({ time: 0, level: STATUS_LEVELS[normalized] ?? 2, status: normalized });
      dataPoints.push({ time: 100, level: STATUS_LEVELS[normalized] ?? 2, status: normalized });
      return dataPoints;
    }

    const sortedEvents = [...statusHistory].sort((a, b) => 
      new Date(a.time).getTime() - new Date(b.time).getTime()
    );

    // Add initial point
    let initialStatus = currentStatus;
    if (!initialStatus && sortedEvents.length > 0) {
      initialStatus = sortedEvents[0].status;
    }
    if (!initialStatus) initialStatus = 'standby';
    
    const normalizedInitial = normalizeStatus(initialStatus);
    dataPoints.push({
      time: 0,
      level: STATUS_LEVELS[normalizedInitial] ?? 2,
      status: normalizedInitial,
    });

    // Add points for each event
    for (const event of sortedEvents) {
      const eventTime = new Date(event.time).getTime();
      if (eventTime >= startTime.getTime() && eventTime <= endTime.getTime()) {
        const normalized = normalizeStatus(event.status);
        const relativeTime = ((eventTime - startTime.getTime()) / totalDuration) * 100;
        dataPoints.push({
          time: relativeTime,
          level: STATUS_LEVELS[normalized] ?? 2,
          status: normalized,
        });
      }
    }

    // Add final point using current status
    const finalStatus = currentStatus || (sortedEvents.length > 0 ? sortedEvents[sortedEvents.length - 1].status : 'standby');
    const normalized = normalizeStatus(finalStatus);
    dataPoints.push({
      time: 100,
      level: STATUS_LEVELS[normalized] ?? 2,
      status: normalized,
    });

    return dataPoints;
  };

  const oscilloscopeData = buildOscilloscopeData();

  // Calculate time divisions
  const calculateTimeDivisions = () => {
    const timeDivisions: Array<{ x: number; label: string; time: Date }> = [];
    switch (timeRange) {
      case '1h':
        for (let i = 0; i <= 4; i++) {
          const minutes = i * 15;
          const divTime = new Date(startTime.getTime() + (minutes * 60 * 1000));
          timeDivisions.push({
            x: (i * 15 / 60) * 100,
            label: `${minutes}m`,
            time: divTime
          });
        }
        break;
      case '8h':
        for (let i = 0; i <= 8; i++) {
          const hours = i;
          const divTime = new Date(startTime.getTime() + (hours * 60 * 60 * 1000));
          timeDivisions.push({
            x: (i / 8) * 100,
            label: `${hours}h`,
            time: divTime
          });
        }
        break;
      case '24h':
        for (let i = 0; i <= 4; i++) {
          const hours = i * 6;
          const divTime = new Date(startTime.getTime() + (hours * 60 * 60 * 1000));
          timeDivisions.push({
            x: (i / 4) * 100,
            label: `${hours}h`,
            time: divTime
          });
        }
        break;
      case '7d':
        for (let i = 0; i <= 7; i++) {
          const days = i;
          const divTime = new Date(startTime.getTime() + (days * 24 * 60 * 60 * 1000));
          timeDivisions.push({
            x: (i / 7) * 100,
            label: `${days}d`,
            time: divTime
          });
        }
        break;
    }
    return timeDivisions;
  };

  const timeDivisions = calculateTimeDivisions();

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
  }, [compact]);

  // Generate SVG oscilloscope
  const renderOscilloscope = () => {
    const statusLevels = [3, 2, 1, 0];
    
    // Convert data points to SVG coordinates (as percentages like PollingOscilloscope)
    const svgPoints: Array<{ x: number; y: number; status: string; timestamp: Date }> = [];
    
    if (oscilloscopeData.length > 0) {
      oscilloscopeData.forEach((point, idx) => {
        const x = point.time; // Already a percentage (0-100)
        // Map Y to 4 states (0-3) with padding
        const levelY = (1 - point.level / 3) * 100; // Invert Y (0 = bottom, 3 = top)
        const paddedY = 8 + (levelY / 100) * 84; // Map to 8-92 range
        const rowHeight = 84 / 4; // Each status row is ~21% of padded height
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
          const nextLevelY = (1 - nextPoint.level / 3) * 100;
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

    // Build SVG path using quadratic bezier (like PollingOscilloscope)
    const buildPath = () => {
      if (svgPoints.length === 0) return '';
      
      let path = `M ${svgPoints[0].x} ${svgPoints[0].y}`;
      
      for (let i = 1; i < svgPoints.length; i++) {
        const prev = svgPoints[i - 1];
        const curr = svgPoints[i];
        
        // Use quadratic bezier for smooth curves
        const cpX = (prev.x + curr.x) / 2;
        const cpY = (prev.y + curr.y) / 2;
        path += ` Q ${cpX} ${prev.y} ${cpX} ${cpY} Q ${cpX} ${curr.y} ${curr.x} ${curr.y}`;
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
          }}
        >
          <svg
            className="status-oscilloscope-svg"
            width="100%"
            height="100%"
            viewBox="0 0 100 100"
            preserveAspectRatio="none"
          >
            {/* Grid lines for each status level */}
            {statusLevels.map((level) => {
              const y = 8 + ((1 - level / 3) * 84);
              return (
                <line
                  key={`grid-${level}`}
                  x1="0"
                  y1={y}
                  x2="100"
                  y2={y}
                  stroke="var(--color-text-dim)"
                  strokeWidth="0.3"
                  opacity="0.2"
                  vectorEffect="non-scaling-stroke"
                />
              );
            })}

            {/* Oscilloscope trace */}
            <path
              d={pathData}
              fill="none"
              stroke="var(--color-text-primary)"
              strokeWidth="0.8"
              className="status-oscilloscope-trace"
              vectorEffect="non-scaling-stroke"
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
              }}
            >
              <svg
                className="status-oscilloscope-svg"
                width="100%"
                height="100%"
                viewBox="0 0 100 100"
                preserveAspectRatio="none"
              >
              {/* Grid lines for each status level */}
              {statusLevels.map((level) => {
                const levelY = (1 - level / 3) * 100;
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
                />
              ))}

              {/* Oscilloscope trace */}
              <path
                d={pathData}
                fill="none"
                stroke="var(--color-text-primary)"
                strokeWidth="0.8"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="status-oscilloscope-trace"
                vectorEffect="non-scaling-stroke"
              />

              {/* Timestamp markers with hover */}
              {oscilloscopeData.map((dataPoint, dataIdx) => {
                const x = dataPoint.time;
                const timestamp = new Date(startTime.getTime() + (dataPoint.time / 100) * totalDuration);
                const hoverRadius = 0.5;
                const levelY = (1 - dataPoint.level / 3) * 100;
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
                          const normalized = normalizeStatus(dataPoint.status);
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
          <span className="status-oscilloscope-x-label-start">PAST</span>
          <div className="status-oscilloscope-x-divisions">
            {timeDivisions.map((div, divIdx) => {
              // Skip first and last (PAST and NOW are already shown)
              if (divIdx === 0 || divIdx === timeDivisions.length - 1) return null;
              return (
                <span
                  key={`time-label-${divIdx}-${div.label}`}
                  className="status-oscilloscope-x-label-division"
                  style={{ left: `${div.x * scaleX}%`, transform: 'translateX(-50%)' }}
                >
                  {div.label}
                </span>
              );
            })}
          </div>
          <span className="status-oscilloscope-x-label-end">NOW</span>
        </div>
      </div>
    );
  };

  const svgHeight = compact ? 40 : 120;

  return (
    <div 
      className={`status-oscilloscope ${compact ? 'status-oscilloscope-compact' : 'status-oscilloscope-full'}`}
      ref={oscilloscopeRef}
      style={{ width: '100%', maxWidth: '100%', overflow: 'hidden', boxSizing: 'border-box' }}
    >
      <div 
        className="status-oscilloscope-display"
        style={{ 
          height: `${svgHeight}px`, 
          width: '100%', 
          maxWidth: '100%', 
          overflow: 'hidden', 
          boxSizing: 'border-box' 
        }}
      >
        {renderOscilloscope()}
      </div>
    </div>
  );
};
