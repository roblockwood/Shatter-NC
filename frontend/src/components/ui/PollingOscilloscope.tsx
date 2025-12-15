import React, { useState, useEffect, useRef } from 'react';
import './PollingOscilloscope.css';

interface PollingDataPoint {
  time: string;
  success: boolean;
  response_time_ms?: number;
}

interface PollingOscilloscopeProps {
  pollingHistory: PollingDataPoint[];
  timeRange?: '1h' | '8h' | '24h' | '7d';
  compact?: boolean; // For tabular UI
  currentOnline?: boolean; // Current online status
}

export const PollingOscilloscope: React.FC<PollingOscilloscopeProps> = ({
  pollingHistory,
  timeRange = '8h',
  compact = false,
  currentOnline = true,
}) => {
  const [hoveredPoint, setHoveredPoint] = useState<{ x: number; y: number; online: boolean; timestamp: Date } | null>(null);
  const [tooltipPosition, setTooltipPosition] = useState<{ x: number; y: number } | null>(null);
  const [oscilloscopeWidth, setOscilloscopeWidth] = useState(180);
  const [scaleX, setScaleX] = useState(1);
  const oscilloscopeRef = useRef<HTMLDivElement>(null);
  const oscilloscopeDataRef = useRef<HTMLDivElement>(null);
  
  // Binary states: ONLINE (top) = 1, OFFLINE (bottom) = 0
  const ONLINE_LEVEL = 1;
  const OFFLINE_LEVEL = 0;
  
  // Build data points from polling history
  const buildOscilloscopeData = () => {
    const dataPoints: Array<{ time: number; level: number; online: boolean }> = [];
    
    if (!pollingHistory || pollingHistory.length === 0) {
      // If no history, show current status
      dataPoints.push({
        time: 0,
        level: currentOnline ? ONLINE_LEVEL : OFFLINE_LEVEL,
        online: currentOnline,
      });
      dataPoints.push({
        time: 100,
        level: currentOnline ? ONLINE_LEVEL : OFFLINE_LEVEL,
        online: currentOnline,
      });
      return dataPoints;
    }

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

    // Sort polling history by time
    const sortedHistory = [...pollingHistory].sort((a, b) => 
      new Date(a.time).getTime() - new Date(b.time).getTime()
    );

    // Filter to time range and convert to data points
    sortedHistory.forEach((poll) => {
      const pollTime = new Date(poll.time).getTime();
      if (pollTime >= startTime.getTime() && pollTime <= endTime.getTime()) {
        const relativeTime = ((pollTime - startTime.getTime()) / totalDuration) * 100;
        dataPoints.push({
          time: relativeTime,
          level: poll.success ? ONLINE_LEVEL : OFFLINE_LEVEL,
          online: poll.success,
        });
      }
    });

    // Add initial point if needed
    if (dataPoints.length === 0 || dataPoints[0].time > 0) {
      const firstPoll = sortedHistory[0];
      const initialOnline = firstPoll ? firstPoll.success : currentOnline;
      dataPoints.unshift({
        time: 0,
        level: initialOnline ? ONLINE_LEVEL : OFFLINE_LEVEL,
        online: initialOnline,
      });
    }

    // Add final point for current status
    dataPoints.push({
      time: 100,
      level: currentOnline ? ONLINE_LEVEL : OFFLINE_LEVEL,
      online: currentOnline,
    });

    return dataPoints;
  };

  const oscilloscopeData = buildOscilloscopeData();
  
  // Generate smooth oscilloscope display with SVG
  const renderOscilloscope = () => {
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
    
    // Binary labels for Y-axis
    const statusLabels = ['ONLINE', 'OFFLINE'];
    const statusLevels = [1, 0];
    
    // Convert data points to SVG coordinates with interpolation for smooth transitions
    const svgPoints: Array<{ x: number; y: number; online: boolean; timestamp: Date }> = [];
    
    if (oscilloscopeData.length > 0) {
      oscilloscopeData.forEach((point, idx) => {
        const x = (point.time / 100) * 100; // Percentage of width
        // Map to Y: ONLINE (top) = 8%, OFFLINE (bottom) = 92%
        const levelY = point.level === ONLINE_LEVEL ? 8 : 92;
        // Add tight oscillation for oscilloscope effect
        const oscillation = Math.sin(x * 2.5) * 2; // Small oscillation
        const y = Math.max(8, Math.min(92, levelY + oscillation));
        
        const timestamp = new Date(startTime.getTime() + (point.time / 100) * totalDuration);
        svgPoints.push({ x, y, online: point.online, timestamp });
        
        // Add intermediate points for smoother transitions
        if (idx < oscilloscopeData.length - 1) {
          const nextPoint = oscilloscopeData[idx + 1];
          const nextX = (nextPoint.time / 100) * 100;
          const nextY = nextPoint.level === ONLINE_LEVEL ? 8 : 92;
          
          // If there's a level change, add transition points
          if (point.level !== nextPoint.level) {
            const steps = 3;
            for (let i = 1; i < steps; i++) {
              const t = i / steps;
              const interpX = x + (nextX - x) * t;
              const interpY = levelY + (nextY - levelY) * t;
              const interpOscillation = Math.sin(interpX * 2.5) * 2;
              const finalY = Math.max(8, Math.min(92, interpY + interpOscillation));
              svgPoints.push({ 
                x: interpX, 
                y: finalY, 
                online: point.online, 
                timestamp: new Date(startTime.getTime() + (interpX / 100) * totalDuration) 
              });
            }
          }
        }
      });
    }
    
    // Calculate time division markers
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
    
    return { svgPoints, statusLabels, statusLevels, timeDivisions };
  };

  const { svgPoints, statusLabels, timeDivisions } = renderOscilloscope();

  // Dynamic width calculation and scaling
  useEffect(() => {
    if (!oscilloscopeRef.current || !oscilloscopeDataRef.current) return;

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
          // In full mode, use a fixed data width that will be scaled down if needed
          const dataWidth = 600;
          setOscilloscopeWidth(dataWidth);
          
          if (containerWidth > 0 && dataWidth > 0) {
            // Scale down if data is wider than container
            setScaleX(Math.min(1, containerWidth / dataWidth));
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
  }, [compact, svgPoints]);

  // Build SVG path from points
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

  const handlePointHover = (point: { x: number; y: number; online: boolean; timestamp: Date }) => {
    if (!oscilloscopeRef.current) return;
    
    const rect = oscilloscopeRef.current.getBoundingClientRect();
    const scaledX = point.x * scaleX;
    const tooltipX = rect.left + scaledX;
    const tooltipY = rect.top + point.y * (rect.height / 100);
    
    // Constrain tooltip to viewport
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;
    const tooltipWidth = 200;
    const tooltipHeight = 60;
    
    let finalX = tooltipX;
    let finalY = tooltipY - tooltipHeight - 8;
    
    if (finalX + tooltipWidth > viewportWidth) {
      finalX = viewportWidth - tooltipWidth - 8;
    }
    if (finalX < 8) {
      finalX = 8;
    }
    if (finalY < 8) {
      finalY = tooltipY + 8;
    }
    if (finalY + tooltipHeight > viewportHeight) {
      finalY = viewportHeight - tooltipHeight - 8;
    }
    
    setTooltipPosition({ x: finalX, y: finalY });
    setHoveredPoint(point);
  };

  const handlePointLeave = () => {
    setHoveredPoint(null);
    setTooltipPosition(null);
  };

  const svgHeight = compact ? 40 : 100;

  return (
    <div className={`polling-oscilloscope ${compact ? 'compact' : ''}`} ref={oscilloscopeRef} style={{ width: '100%', maxWidth: '100%', overflow: 'hidden', boxSizing: 'border-box' }}>
      {!compact && (
        <div className="oscilloscope-labels">
          {statusLabels.map((label) => (
            <div key={label} className="oscilloscope-label">
              {label}
            </div>
          ))}
        </div>
      )}
      <div className="oscilloscope-display-wrapper" style={{ width: '100%', maxWidth: '100%', overflow: 'hidden', boxSizing: 'border-box' }}>
        <div className="oscilloscope-display" style={{ height: `${svgHeight}px`, width: '100%', maxWidth: '100%', overflow: 'hidden', boxSizing: 'border-box' }}>
          <div 
            ref={oscilloscopeDataRef}
            className="oscilloscope-data"
            style={{
              transform: `scaleX(${scaleX})`,
              transformOrigin: 'left center',
              width: `${oscilloscopeWidth}px`,
              maxWidth: 'none',
              boxSizing: 'border-box',
            }}
          >
            <svg
              className="oscilloscope-svg"
              width="100%"
              height="100%"
              viewBox="0 0 100 100"
              preserveAspectRatio="none"
            >
              {/* Grid lines for binary states */}
              <line
                x1="0"
                y1="8"
                x2="100"
                y2="8"
                className="oscilloscope-grid-line"
                stroke="#00ff00"
                strokeWidth="0.5"
                opacity="0.2"
              />
              <line
                x1="0"
                y1="92"
                x2="100"
                y2="92"
                className="oscilloscope-grid-line"
                stroke="#ff0000"
                strokeWidth="0.5"
                opacity="0.2"
              />
              
              {/* Time division lines */}
              {timeDivisions.map((div) => (
                <g key={`div-${div.x}-${div.label}`}>
                  <line
                    x1={div.x}
                    y1="0"
                    x2={div.x}
                    y2="100"
                    className="oscilloscope-time-division-line"
                    stroke="#00ff00"
                    strokeWidth="0.3"
                    opacity="0.2"
                    strokeDasharray="1 1"
                    vectorEffect="non-scaling-stroke"
                  />
                </g>
              ))}
              
              {/* Trace path */}
              <path
                d={buildPath()}
                className="oscilloscope-trace"
                fill="none"
                stroke={currentOnline ? "#00ff00" : "#ff0000"}
                strokeWidth="0.8"
                vectorEffect="non-scaling-stroke"
              />
              
              {/* Timestamp indicators with hover areas */}
              {svgPoints.map((point, idx) => {
                if (idx % Math.max(1, Math.floor(svgPoints.length / 20)) !== 0) return null; // Show every Nth point
                const hoverRadius = 0.5;
                return (
                  <g key={`point-${idx}`}>
                    <rect
                      x={point.x - hoverRadius}
                      y="0"
                      width={hoverRadius * 2}
                      height="100"
                      className="oscilloscope-timestamp-hover-area"
                      fill="transparent"
                      onMouseEnter={() => handlePointHover(point)}
                      onMouseLeave={handlePointLeave}
                    />
                    <line
                      x1={point.x}
                      y1="0"
                      x2={point.x}
                      y2="100"
                      className="oscilloscope-timestamp-line"
                      stroke={point.online ? "#00ff00" : "#ff0000"}
                      strokeWidth="0.5"
                      opacity="0.25"
                      strokeDasharray="3 2"
                      shapeRendering="crispEdges"
                      vectorEffect="non-scaling-stroke"
                      pointerEvents="none"
                    />
                  </g>
                );
              })}
            </svg>
          </div>
        </div>
        {!compact && (
          <div className="oscilloscope-x-axis">
            <span className="oscilloscope-x-axis-label">PAST</span>
            {timeDivisions.map((div, idx) => (
              <span
                key={`label-${idx}`}
                className="oscilloscope-x-axis-label"
                style={{
                  left: `${div.x * scaleX}%`,
                }}
              >
                {div.label}
              </span>
            ))}
            <span className="oscilloscope-x-axis-label" style={{ right: '0' }}>NOW</span>
          </div>
        )}
      </div>
      
      {/* Tooltip */}
      {hoveredPoint && tooltipPosition && (
        <div
          className="oscilloscope-tooltip"
          style={{
            position: 'fixed',
            left: `${tooltipPosition.x}px`,
            top: `${tooltipPosition.y}px`,
          }}
        >
          <div className="tooltip-status">
            {hoveredPoint.online ? 'ONLINE' : 'OFFLINE'}
          </div>
          <div className="tooltip-time">
            {hoveredPoint.timestamp.toLocaleString()}
          </div>
        </div>
      )}
    </div>
  );
};

