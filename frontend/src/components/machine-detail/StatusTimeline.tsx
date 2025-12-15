import React, { useState, useEffect } from 'react';
import { API_BASE_URL } from '../../config/api';
import './StatusTimeline.css';

interface StatusEvent {
  time: string;
  status: string;
  previous_status?: string;
}

interface StatusTimelineProps {
  machineId: number;
  currentStatus?: string; // Current machine status from WebSocket
  isOnline?: boolean; // Whether machine is online
  onExpand?: () => void;
}

type TimeRange = '1h' | '8h' | '24h' | '7d';

export const StatusTimeline: React.FC<StatusTimelineProps> = ({ machineId, currentStatus, isOnline, onExpand }) => {
  const [timeRange, setTimeRange] = useState<TimeRange>('24h');
  const [events, setEvents] = useState<StatusEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [hoveredPoint, setHoveredPoint] = useState<{ x: number; y: number; status: string; timestamp: Date } | null>(null);
  const [tooltipPosition, setTooltipPosition] = useState<{ x: number; y: number } | null>(null);
  const [oscilloscopeWidth, setOscilloscopeWidth] = useState(180);
  const [scaleX, setScaleX] = useState(1);
  const oscilloscopeRef = React.useRef<HTMLDivElement>(null);
  const oscilloscopeDataRef = React.useRef<HTMLDivElement>(null);
  
  // Status mapping for Y-axis (oscilloscope) - using actual machine statuses
  // Order: Operating (top), Standby, Stopped, Error, Off (bottom)
  const STATUS_LEVELS: { [key: string]: number } = {
    'operating': 4,
    'standby': 3,
    'stopped': 2,
    'error': 1,
    'off': 0,
  };
  
  // Normalize status string to actual machine status key
  // Machine statuses: off, standby, error, operating, stopped
  // Returns the normalized machine status string
  const normalizeStatus = (status: string | undefined, online?: boolean): string => {
    // If machine is explicitly offline, return 'off'
    if (online === false) {
      return 'off';
    }
    if (!status) return 'standby'; // Default to standby
    const lower = status.toLowerCase().trim();
    
    // Map to actual machine statuses
    if (lower === 'operating') {
      return 'operating';
    }
    if (lower === 'standby') {
      return 'standby';
    }
    if (lower === 'stopped') {
      return 'stopped';
    }
    if (lower === 'error') {
      return 'error';
    }
    if (lower === 'off') {
      return 'off';
    }
    
    // Fallback mappings for legacy/compatibility
    if (lower.includes('error') || lower === 'occurred' || lower.includes('occurred')) {
      return 'error';
    }
    if (lower.includes('alarm')) {
      return 'error'; // Treat alarm as error for display
    }
    if (lower.includes('running') || lower.includes('operating')) {
      return 'operating';
    }
    if (lower.includes('idle') || lower.includes('standby')) {
      return 'standby';
    }
    if (lower.includes('stopped') || lower.includes('off')) {
      return 'stopped';
    }
    return 'standby'; // default to standby
  };

  useEffect(() => {
    const fetchStatusHistory = async () => {
      try {
        setLoading(true);
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

        const response = await fetch(
          `${API_BASE_URL}/api/machines/${machineId}/status-history?start_time=${startTime.toISOString()}&end_time=${endTime.toISOString()}&limit=1000`
        );
        
        if (response.ok) {
          const data = await response.json();
          setEvents(data);
        }
      } catch (error) {
        console.error('Error fetching status history:', error);
      } finally {
        setLoading(false);
      }
    };

    fetchStatusHistory();
    // Refresh every 60 seconds
    const interval = setInterval(fetchStatusHistory, 60000);
    return () => clearInterval(interval);
  }, [machineId, timeRange]);

  // Calculate oscilloscope scale based on container size
  useEffect(() => {
    const updateScale = () => {
      // Use requestAnimationFrame to ensure DOM is updated
      requestAnimationFrame(() => {
        if (oscilloscopeRef.current && oscilloscopeDataRef.current) {
          const container = oscilloscopeRef.current;
          const dataElement = oscilloscopeDataRef.current;
          
          // Get available width (container minus Y-axis labels and padding)
          const containerWidth = container.offsetWidth;
          const availableWidth = containerWidth - 70 - 32 - 32; // Y-axis + padding
          
          // Get actual rendered width of the oscilloscope data
          const dataWidth = dataElement.scrollWidth;
          
          if (dataWidth > 0 && availableWidth > 0) {
            // Calculate scale factor to fit content
            const scale = Math.min(1, availableWidth / dataWidth);
            setScaleX(scale);
          }
        }
      });
    };

    // Initial calculation with a small delay to ensure DOM is ready
    const initialTimer = setTimeout(updateScale, 100);
    
    // Set up ResizeObserver to watch for container size changes
    const resizeObserver = new ResizeObserver(() => {
      updateScale();
    });
    
    if (oscilloscopeRef.current) {
      resizeObserver.observe(oscilloscopeRef.current);
    }
    
    // Also watch for window resize
    window.addEventListener('resize', updateScale);

    return () => {
      clearTimeout(initialTimer);
      resizeObserver.disconnect();
      window.removeEventListener('resize', updateScale);
    };
  }, [oscilloscopeWidth]); // Recalculate when width changes

  // Build oscilloscope data points
  const buildOscilloscopeData = () => {
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
    const dataPoints: Array<{ time: number; level: number; status: string }> = [];

    // If no events, still show current status
    if (events.length === 0) {
      const normalized = normalizeStatus(currentStatus || 'standby', isOnline);
      dataPoints.push({
        time: 0,
        level: STATUS_LEVELS[normalized] ?? 3,
        status: normalized,
      });
      dataPoints.push({
        time: 100,
        level: STATUS_LEVELS[normalized] ?? 3,
        status: normalized,
      });
      return dataPoints;
    }

    const sortedEvents = [...events].sort((a, b) => 
      new Date(a.time).getTime() - new Date(b.time).getTime()
    );

    // Add initial point - prefer currentStatus if available (most accurate)
    // Otherwise use first event status
    let initialStatus = currentStatus;
    if (!initialStatus && sortedEvents.length > 0) {
      const firstEvent = sortedEvents[0];
      const firstEventTime = new Date(firstEvent.time).getTime();
      if (firstEventTime >= startTime.getTime()) {
        initialStatus = firstEvent.status;
      }
    }
    if (!initialStatus) initialStatus = 'standby';
    
    const normalizedInitial = normalizeStatus(initialStatus, isOnline);
    dataPoints.push({
      time: 0,
      level: STATUS_LEVELS[normalizedInitial] ?? 3,
      status: normalizedInitial,
    });

    // Add points for each event - normalize each status carefully
    for (const event of sortedEvents) {
      const eventTime = new Date(event.time).getTime();
      if (eventTime >= startTime.getTime() && eventTime <= endTime.getTime()) {
        const normalized = normalizeStatus(event.status, undefined); // Historical events don't have isOnline
        const relativeTime = ((eventTime - startTime.getTime()) / totalDuration) * 100;
        dataPoints.push({
          time: relativeTime,
          level: STATUS_LEVELS[normalized] ?? 3,
          status: normalized,
        });
      }
    }

    // Add final point - ALWAYS use currentStatus from WebSocket if available (most accurate)
    // This ensures the "NOW" point reflects the actual current machine state
    const finalStatus = currentStatus || (sortedEvents.length > 0 ? sortedEvents[sortedEvents.length - 1].status : 'standby');
    const normalized = normalizeStatus(finalStatus, isOnline);
    dataPoints.push({
      time: 100,
      level: STATUS_LEVELS[normalized] ?? 3,
      status: normalized,
    });
    
    // If currentStatus is provided and different from last event, we might want to add a transition point
    // But for now, the final point at 100% should represent current state

    return dataPoints;
  };

  const oscilloscopeData = buildOscilloscopeData();
  
  // Generate smooth oscilloscope display with SVG
  const renderOscilloscope = () => {
    // Calculate time range for timestamp calculation
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
    
    // Status labels for Y-axis
    const statusLabels = ['OPERATING', 'STANDBY', 'STOPPED', 'ERROR', 'OFF'];
    const statusLevels = [4, 3, 2, 1, 0]; // Corresponding levels
    
    // Convert data points to SVG coordinates with interpolation for smooth transitions
    const svgPoints: Array<{ x: number; y: number; status: string; timestamp: Date }> = [];
    
    if (oscilloscopeData.length > 0) {
      oscilloscopeData.forEach((point, idx) => {
        const x = (point.time / 100) * 100; // Percentage of width
        // Ensure Y stays within row boundaries (each status level gets 20% of height)
        const levelY = (1 - point.level / 4) * 100; // Invert Y (0 = bottom, 4 = top)
        // Add tight oscillation to keep it within the row (oscilloscope-style)
        const rowCenter = levelY;
        const rowHeight = 20; // Each status row is 20% of total height
        // Much tighter oscillation frequency for realistic oscilloscope effect
        const oscillation = Math.sin(x * 2.5) * (rowHeight * 0.12); // Tight, high-frequency oscillation
        const y = Math.max(rowCenter - rowHeight/2 + 2, Math.min(rowCenter + rowHeight/2 - 2, rowCenter + oscillation));
        
        const timestamp = new Date(startTime.getTime() + (point.time / 100) * totalDuration);
        svgPoints.push({ x, y, status: point.status, timestamp });
        
        // Add intermediate points for smoother transitions
        if (idx < oscilloscopeData.length - 1) {
          const nextPoint = oscilloscopeData[idx + 1];
          const nextX = (nextPoint.time / 100) * 100;
          const nextLevelY = (1 - nextPoint.level / 4) * 100;
          
          // If there's a level change, add transition points
          if (Math.abs(point.level - nextPoint.level) > 0.1) {
            const steps = 3;
            for (let i = 1; i < steps; i++) {
              const t = i / steps;
              const interpX = x + (nextX - x) * t;
              const interpY = rowCenter + (nextLevelY - rowCenter) * t;
              const interpOscillation = Math.sin(interpX * 2.5) * (rowHeight * 0.12);
              const finalY = Math.max(interpY - rowHeight/2 + 2, Math.min(interpY + rowHeight/2 - 2, interpY + interpOscillation));
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
    
    // Calculate time division markers based on time range
    const timeDivisions: Array<{ x: number; label: string; time: Date }> = [];
    switch (timeRange) {
      case '1h':
        // Every 15 minutes for 1 hour
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
        // Every hour for 8 hours
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
        // Every 6 hours for 24 hours
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
        // Every day for 7 days
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
    
    return { svgPoints, statusLabels, statusLevels, startTime, endTime, totalDuration, timeDivisions };
  };

  const { svgPoints, statusLabels, statusLevels, startTime, endTime, totalDuration, timeDivisions } = renderOscilloscope();
  
  // Recalculate scale after SVG is rendered
  useEffect(() => {
    const timer = setTimeout(() => {
      if (oscilloscopeRef.current && oscilloscopeDataRef.current) {
        const container = oscilloscopeRef.current;
        const dataElement = oscilloscopeDataRef.current;
        
        const containerWidth = container.offsetWidth;
        const availableWidth = containerWidth - 70 - 32 - 32;
        const dataWidth = dataElement.scrollWidth;
        
        if (dataWidth > 0 && availableWidth > 0) {
          const scale = Math.min(1, availableWidth / dataWidth);
          setScaleX(scale);
        }
      }
    }, 50);
    return () => clearTimeout(timer);
  }, [svgPoints, oscilloscopeWidth]);

  return (
    <div className="status-timeline">
      <div className="status-timeline-header">
        <div className="status-timeline-title-row">
          <span>┌─ STATUS TIMELINE {'─'.repeat(25)}┐</span>
        </div>
      </div>
      <div className="status-timeline-controls">
        <button
          className={`time-range-btn ${timeRange === '1h' ? 'active' : ''}`}
          onClick={() => setTimeRange('1h')}
        >
          [1H]
        </button>
        <button
          className={`time-range-btn ${timeRange === '8h' ? 'active' : ''}`}
          onClick={() => setTimeRange('8h')}
        >
          [8H]
        </button>
        <button
          className={`time-range-btn ${timeRange === '24h' ? 'active' : ''}`}
          onClick={() => setTimeRange('24h')}
        >
          [24H]
        </button>
        <button
          className={`time-range-btn ${timeRange === '7d' ? 'active' : ''}`}
          onClick={() => setTimeRange('7d')}
        >
          [7D]
        </button>
      </div>
      <div className="status-timeline-content">
        {loading ? (
          <div className="timeline-loading">LOADING...</div>
        ) : oscilloscopeData.length === 0 ? (
          <div className="timeline-empty">NO STATUS DATA</div>
        ) : (
          <div className="oscilloscope-display" ref={oscilloscopeRef}>
            <div className="oscilloscope-display-wrapper">
              <div className="oscilloscope-grid">
                {/* Y-axis labels and SVG oscilloscope */}
                <div className="oscilloscope-labels-column">
                  {statusLabels.map((label, idx) => (
                    <div key={idx} className="oscilloscope-row">
                      <span className="oscilloscope-y-label">
                        {label.padEnd(8)}
                      </span>
                      <span className="oscilloscope-line">│</span>
                    </div>
                  ))}
                </div>
                <div className="oscilloscope-svg-container" ref={oscilloscopeDataRef}>
                  <svg 
                    className="oscilloscope-svg"
                    viewBox="0 0 100 100"
                    preserveAspectRatio="none"
                    style={{ 
                      transform: `scaleX(${scaleX})`, 
                      transformOrigin: 'left center'
                    }}
                  >
                    {/* Grid lines for each status level */}
                    {statusLevels.map((level, idx) => (
                      <line 
                        key={idx}
                        x1="0" 
                        y1={100 - (level / 4) * 100} 
                        x2="100" 
                        y2={100 - (level / 4) * 100}
                        stroke="var(--color-text-dim)"
                        strokeWidth="0.5"
                        opacity="0.3"
                      />
                    ))}
                    {/* Time division markers */}
                    {timeDivisions.map((div, idx) => (
                      <line
                        key={`time-div-${idx}`}
                        x1={div.x}
                        y1="0"
                        x2={div.x}
                        y2="100"
                        stroke="var(--color-text-dim)"
                        strokeWidth="0.3"
                        strokeDasharray="1 1"
                        opacity="0.2"
                        shapeRendering="crispEdges"
                        className="oscilloscope-time-division"
                      />
                    ))}
                    {/* Oscilloscope trace - smooth curve with oscillation */}
                    {svgPoints.length > 1 && (
                      <path
                        d={(() => {
                          // Create smooth path using quadratic bezier curves
                          let pathD = `M ${svgPoints[0].x},${svgPoints[0].y}`;
                          for (let i = 1; i < svgPoints.length; i++) {
                            const prev = svgPoints[i - 1];
                            const curr = svgPoints[i];
                            
                            // Use smooth quadratic bezier for transitions
                            const midX = (prev.x + curr.x) / 2;
                            const midY = (prev.y + curr.y) / 2;
                            
                            pathD += ` Q ${prev.x},${prev.y} ${midX},${midY} T ${curr.x},${curr.y}`;
                          }
                          return pathD;
                        })()}
                        fill="none"
                        stroke="var(--color-text-primary)"
                        strokeWidth="0.8"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        vectorEffect="non-scaling-stroke"
                        className="oscilloscope-trace"
                      />
                    )}
                    {/* Timestamp markers - vertical lines */}
                    {oscilloscopeData.map((dataPoint, dataIdx) => {
                      const x = (dataPoint.time / 100) * 100;
                      const timestamp = new Date(startTime.getTime() + (dataPoint.time / 100) * totalDuration);
                      
                      return (
                        <line
                          key={dataIdx}
                          x1={x}
                          y1="0"
                          x2={x}
                          y2="100"
                          stroke="var(--color-text-primary)"
                          strokeWidth="0.5"
                          strokeDasharray="3 2"
                          opacity="0.25"
                          shapeRendering="crispEdges"
                          className="oscilloscope-timestamp-line"
                          data-timestamp-idx={dataIdx}
                          onMouseEnter={(e) => {
                            const rect = e.currentTarget.getBoundingClientRect();
                            const containerRect = e.currentTarget.closest('.oscilloscope-display')?.getBoundingClientRect();
                            if (containerRect) {
                              const normalized = normalizeStatus(dataPoint.status, isOnline);
                              setHoveredPoint({
                                x: x,
                                y: (1 - (STATUS_LEVELS[normalized] ?? 3) / 4) * 100,
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
                      );
                    })}
                  </svg>
                </div>
              </div>
            </div>
            {hoveredPoint && tooltipPosition && (
              <div 
                className="oscilloscope-tooltip"
                style={{
                  left: `${tooltipPosition.x}px`,
                  top: `${tooltipPosition.y}px`,
                }}
              >
                {hoveredPoint.status}<br/>
                {hoveredPoint.timestamp.toLocaleString()}
              </div>
            )}
            <div className="oscilloscope-x-axis">
              <span className="oscilloscope-x-label-start">PAST</span>
              <div className="oscilloscope-x-divisions">
                {timeDivisions.map((div, idx) => {
                  // Skip first and last (PAST and NOW are already shown)
                  if (idx === 0 || idx === timeDivisions.length - 1) return null;
                  return (
                    <span
                      key={`time-label-${idx}`}
                      className="oscilloscope-x-label-division"
                      style={{ left: `${div.x * scaleX}%`, transform: 'translateX(-50%)' }}
                    >
                      {div.label}
                    </span>
                  );
                })}
              </div>
              <span className="oscilloscope-x-label-end">NOW</span>
            </div>
          </div>
        )}
      </div>
      <div className="status-timeline-footer">
        └{'─'.repeat(42)}┘
      </div>
    </div>
  );
};

