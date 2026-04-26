import React, { useState, useEffect, useMemo } from 'react';
import { API_BASE_URL } from '../../config/api';
import { useBetaMode } from '../../hooks/useBetaMode';
import { useLocalChartTimeAxisMode } from '../../hooks/useLocalChartTimeAxisMode';
import {
  buildOscilloscopeAxisDivisionLabels,
  getOscilloscopeTicksForMode,
  oscilloscopeAxisEndLabels,
} from '../../utils/chartTimeAxis';
import { ChartTimeAxisToggle } from '../ui/ChartTimeAxisToggle';
import { earlierIsoTimestamp } from '../ui/pollingFreshness';
import { PollingStatusLight } from '../ui/PollingStatusLight';
import '../ui/TerminalBox.css';
import { TERMINAL_RULE_FILL } from '../../utils/terminalAsciiRule';
import './StatusTimeline.css';

interface StatusEvent {
  time: string;
  status: string;
  previous_status?: string;
  error?: string;
  is_heartbeat?: boolean;
}

interface AlarmHistoryEvent {
  time: string;
  alarm_code: string;
  alarm_message: string;
}

interface CycleHistoryEntryForTimeline {
  start_time: string;
  end_time: string;
  part_count: number;
}

interface StatusTimelineProps {
  machineId: number;
  currentStatus?: string; // Current machine status from WebSocket
  isOnline?: boolean; // Whether machine is online
  currentError?: string; // Current error message if machine is offline
  onExpand?: () => void;
  /** Last successful fast CNC poll (ISO). With API fetch time, only the older instant is used for the light. */
  machineLastSuccessfulPollAt?: string | null;
}

type TimeRange = '1h' | '8h' | '24h' | '7d';

export const StatusTimeline: React.FC<StatusTimelineProps> = ({
  machineId,
  currentStatus,
  isOnline,
  currentError,
  onExpand: _onExpand,
  machineLastSuccessfulPollAt,
}) => {
  const { isBetaMode } = useBetaMode();
  const { timeAxisMode, toggleTimeAxisMode } = useLocalChartTimeAxisMode(
    `speedio-${machineId}-status-timeline`
  );
  const [timeRange, setTimeRange] = useState<TimeRange>('24h');
  const [events, setEvents] = useState<StatusEvent[]>([]);
  const [alarmEvents, setAlarmEvents] = useState<AlarmHistoryEvent[]>([]);
  const [cycleEntries, setCycleEntries] = useState<CycleHistoryEntryForTimeline[]>([]);
  const [loading, setLoading] = useState(true);
  const [hoveredPoint, setHoveredPoint] = useState<{ x: number; y: number; status: string; timestamp: Date; error?: string; is_heartbeat?: boolean; isLatest?: boolean } | null>(null);
  const [tooltipPosition, setTooltipPosition] = useState<{ x: number; y: number } | null>(null);
  const [oscilloscopeWidth] = useState(180);
  const [scaleX, setScaleX] = useState(1);
  const [colorMode, setColorMode] = useState<boolean>(() => {
    return localStorage.getItem('oscilloscopeColorMode') === 'true';
  });
  const [lastFetchSuccessAt, setLastFetchSuccessAt] = useState<string | null>(null);
  const statusLightLastUpdatedAt = useMemo(
    () => earlierIsoTimestamp(lastFetchSuccessAt, machineLastSuccessfulPollAt),
    [lastFetchSuccessAt, machineLastSuccessfulPollAt],
  );
  const oscilloscopeRef = React.useRef<HTMLDivElement>(null);
  const oscilloscopeDataRef = React.useRef<HTMLDivElement>(null);
  
  // Update localStorage when colorMode changes
  useEffect(() => {
    localStorage.setItem('oscilloscopeColorMode', String(colorMode));
  }, [colorMode]);
  
  // Status mapping for Y-axis (oscilloscope) - using actual machine statuses
  // Order: Operating (top), Standby, Stopped, Error, Off (bottom)
  const STATUS_LEVELS: { [key: string]: number } = {
    'operating': 4,
    'standby': 3,
    'stopped': 2,
    'error': 1,
    'off': 0,
  };
  
  // Color mapping for status levels
  const STATUS_COLORS: { [key: string]: string } = {
    'operating': '#00ff00', // green
    'standby': '#ffff00',    // yellow
    'stopped': '#ff8800',    // orange
    'error': '#ff0000',      // red
    'off': '#808080',        // grey
  };
  
  // Helper to get color for a Y position (8-92, where 8 is top, 92 is bottom)
  const getColorForY = (y: number): string => {
    // Y is in padded range: 8 (top) to 92 (bottom)
    // Status levels: operating=4 (top), standby=3, stopped=2, error=1, off=0 (bottom)
    // Invert Y: higher Y = lower level
    const normalizedY = (y - 8) / 84; // 0 to 1, where 0 = top, 1 = bottom
    const invertedY = 1 - normalizedY; // Invert: 0 = bottom, 1 = top
    const level = invertedY * 4; // 0 to 4, where 0 = off (bottom), 4 = operating (top)
    
    // Map level to status colors with extended smooth interpolation zones
    // Level 0 = off (grey), Level 1 = error (red), Level 2 = stopped (orange), Level 3 = standby (yellow), Level 4 = operating (green)
    // Extended transition zones for smoother color changes
    
    if (level <= 0.3) {
      // Bottom: off (grey) - pure grey
      return STATUS_COLORS['off'];
    } else if (level <= 1.2) {
      // Extended transition zone around level 1: error (red)
      if (level <= 1.0) {
        // Transition from off (0.3) to error (1.0) - wider zone
        const t = (level - 0.3) / 0.7; // 0 to 1 over wider range
        return interpolateColor(STATUS_COLORS['off'], STATUS_COLORS['error'], t);
      } else {
        // Transition from error (1.0) to stopped (1.2) - extended
        const t = (level - 1.0) / 0.2; // 0 to 1
        return interpolateColor(STATUS_COLORS['error'], STATUS_COLORS['stopped'], t);
      }
    } else if (level <= 2.2) {
      // Extended transition zone around level 2: stopped (orange)
      if (level <= 2.0) {
        // Transition from error (1.2) to stopped (2.0) - extended
        const t = (level - 1.2) / 0.8; // 0 to 1 over wider range
        return interpolateColor(STATUS_COLORS['error'], STATUS_COLORS['stopped'], t);
      } else {
        // Transition from stopped (2.0) to standby (2.2) - extended
        const t = (level - 2.0) / 0.2; // 0 to 1
        return interpolateColor(STATUS_COLORS['stopped'], STATUS_COLORS['standby'], t);
      }
    } else if (level <= 3.2) {
      // Extended transition zone around level 3: standby (yellow)
      if (level <= 3.0) {
        // Transition from stopped (2.2) to standby (3.0) - extended
        const t = (level - 2.2) / 0.8; // 0 to 1 over wider range
        return interpolateColor(STATUS_COLORS['stopped'], STATUS_COLORS['standby'], t);
      } else {
        // Transition from standby (3.0) to operating (3.2) - extended
        const t = (level - 3.0) / 0.2; // 0 to 1
        return interpolateColor(STATUS_COLORS['standby'], STATUS_COLORS['operating'], t);
      }
    } else {
      // Top: operating (green)
      if (level <= 4.0) {
        // Transition from standby (3.2) to operating (4.0) - extended
        const t = (level - 3.2) / 0.8; // 0 to 1 over wider range
        return interpolateColor(STATUS_COLORS['standby'], STATUS_COLORS['operating'], t);
      }
      return STATUS_COLORS['operating'];
    }
  };
  
  // Helper to interpolate between two hex colors
  const interpolateColor = (color1: string, color2: string, t: number): string => {
    const hex1 = color1.replace('#', '');
    const hex2 = color2.replace('#', '');
    const r1 = parseInt(hex1.substr(0, 2), 16);
    const g1 = parseInt(hex1.substr(2, 2), 16);
    const b1 = parseInt(hex1.substr(4, 2), 16);
    const r2 = parseInt(hex2.substr(0, 2), 16);
    const g2 = parseInt(hex2.substr(2, 2), 16);
    const b2 = parseInt(hex2.substr(4, 2), 16);
    
    const r = Math.round(r1 + (r2 - r1) * t);
    const g = Math.round(g1 + (g2 - g1) * t);
    const b = Math.round(b1 + (b2 - b1) * t);
    
    return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`;
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
          const eventsWithHeartbeat = data.map((event: StatusEvent) => ({
            ...event,
            is_heartbeat:
              event.previous_status !== undefined &&
              event.previous_status !== null &&
              event.previous_status.toLowerCase() === event.status.toLowerCase(),
          }));
          setEvents(eventsWithHeartbeat);
          setLastFetchSuccessAt(new Date().toISOString());
        }

        const alarmsResponse = await fetch(
          `${API_BASE_URL}/api/machines/${machineId}/alarms?start_time=${startTime.toISOString()}&end_time=${endTime.toISOString()}&limit=1000`
        );
        if (alarmsResponse.ok) {
          const alarmData = await alarmsResponse.json();
          setAlarmEvents(Array.isArray(alarmData) ? alarmData : []);
        }

        const cycleResponse = await fetch(
          `${API_BASE_URL}/api/machines/${machineId}/cycle-history?since=${startTime.toISOString()}&limit=100`
        );
        if (cycleResponse.ok) {
          const cycleData = await cycleResponse.json();
          const arr = Array.isArray(cycleData) ? cycleData : [];
          const minimalCycles: CycleHistoryEntryForTimeline[] = arr.map((c: { start_time: string; end_time: string; part_count?: number }) => ({
            start_time: c.start_time,
            end_time: c.end_time,
            part_count: c.part_count ?? 0,
          }));
          setCycleEntries(minimalCycles);
        } else {
          setCycleEntries([]);
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
          
          // Only calculate if container has valid dimensions
          if (containerWidth > 0) {
            const availableWidth = containerWidth - 70 - 32 - 32; // Y-axis + padding
            
            // Get actual rendered width of the oscilloscope data
            const dataWidth = dataElement.scrollWidth;
            
            if (dataWidth > 0 && availableWidth > 0) {
              // Calculate scale factor to fit content
              const scale = Math.min(1, availableWidth / dataWidth);
              setScaleX(scale);
            } else {
              // Fallback to scale 1 if calculation fails
              setScaleX(1);
            }
          }
        }
      });
    };

    // Multiple attempts to ensure container is sized (especially important for hover panes)
    const initialTimer1 = setTimeout(updateScale, 100);
    const initialTimer2 = setTimeout(updateScale, 300);
    const initialTimer3 = setTimeout(updateScale, 600);
    
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
      clearTimeout(initialTimer1);
      clearTimeout(initialTimer2);
      clearTimeout(initialTimer3);
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
    const dataPoints: Array<{ time: number; level: number; status: string; error?: string; is_heartbeat?: boolean }> = [];

    // If no events: only show a span when we have live data (currentStatus/isOnline from WebSocket).
    // Otherwise we have no data for this window — don't assume a state.
    if (events.length === 0) {
      const hasLiveData = currentStatus !== undefined || isOnline !== undefined;
      if (hasLiveData) {
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
      }
      return dataPoints;
    }

    const sortedEvents = [...events].sort((a, b) =>
      new Date(a.time).getTime() - new Date(b.time).getTime()
    );

    // Do NOT add a synthetic point at time 0 — we only interpolate between actual status events.
    // Starting the line at the left edge would imply the machine was in some state before the first event.

    // Add points for each event within the time window
    for (const event of sortedEvents) {
      const eventTime = new Date(event.time).getTime();
      if (eventTime >= startTime.getTime() && eventTime <= endTime.getTime()) {
        const normalized = normalizeStatus(event.status, undefined); // Historical events don't have isOnline
        const relativeTime = ((eventTime - startTime.getTime()) / totalDuration) * 100;
        dataPoints.push({
          time: relativeTime,
          level: STATUS_LEVELS[normalized] ?? 3,
          status: normalized,
          error: event.error,
          is_heartbeat: event.is_heartbeat,
        });
      }
    }

    // Add "now" point at 100% only when we have live currentStatus (polling is running and we know state).
    // Otherwise we would be assuming the last event's state continued to now.
    if (currentStatus !== undefined) {
      const finalStatus = currentStatus;
      const normalized = normalizeStatus(finalStatus, isOnline);
      dataPoints.push({
        time: 100,
        level: STATUS_LEVELS[normalized] ?? 3,
        status: normalized,
        error: !isOnline && currentError ? currentError : undefined,
      });
    }

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
    
    // Convert data points to SVG coordinates — flat Y per status level (digital step display)
    const svgPoints: Array<{ x: number; y: number; status: string; timestamp: Date; error?: string; is_heartbeat?: boolean }> = [];
    
    if (oscilloscopeData.length > 0) {
      oscilloscopeData.forEach((point) => {
        const x = (point.time / 100) * 100;
        const levelY = (1 - point.level / 4) * 100; // Invert Y (0 = bottom, 4 = top)
        const y = 8 + (levelY / 100) * 84; // Map to 8-92 range, flat within row
        const timestamp = new Date(startTime.getTime() + (point.time / 100) * totalDuration);
        const error = point.time === 100 && !isOnline && currentError ? currentError : undefined;
        svgPoints.push({ x, y, status: point.status, timestamp, error, is_heartbeat: point.is_heartbeat });
      });
    }
    
    const timeTicks = getOscilloscopeTicksForMode(timeRange, startTime, endTime, timeAxisMode);
    const timeDivisions = buildOscilloscopeAxisDivisionLabels(
      timeRange,
      timeTicks,
      endTime,
      timeAxisMode
    );
    const axisEnds = oscilloscopeAxisEndLabels(timeRange, startTime, endTime, timeAxisMode);

    return {
      svgPoints,
      statusLabels,
      statusLevels,
      startTime,
      endTime,
      totalDuration,
      timeDivisions,
      axisEnds,
    };
  };

  const {
    svgPoints,
    statusLabels,
    statusLevels,
    startTime,
    endTime: _endTime,
    totalDuration,
    timeDivisions,
    axisEnds,
  } = renderOscilloscope();
  
  // Recalculate scale after SVG is rendered and when component becomes visible.
  // IMPORTANT: do not depend on svgPoints directly here, since it's a new array every render
  // and would cause this effect to run on every render and continually call setScaleX.
  useEffect(() => {
    const updateScale = () => {
      if (oscilloscopeRef.current && oscilloscopeDataRef.current) {
        const container = oscilloscopeRef.current;
        const dataElement = oscilloscopeDataRef.current;
        
        const containerWidth = container.offsetWidth;
        // Only calculate if container has valid dimensions
        if (containerWidth > 0) {
          const availableWidth = containerWidth - 70 - 32 - 32;
          const dataWidth = dataElement.scrollWidth;
          
          if (dataWidth > 0 && availableWidth > 0) {
            const scale = Math.min(1, availableWidth / dataWidth);
            setScaleX(scale);
          } else {
            // Fallback to scale 1 if calculation fails
            setScaleX(1);
          }
        }
      }
    };

    // Use multiple attempts to ensure container is sized
    const timer1 = setTimeout(updateScale, 50);
    const timer2 = setTimeout(updateScale, 200);
    const timer3 = setTimeout(updateScale, 500);
    
    // Also use IntersectionObserver to recalculate when component becomes visible
    let observer: IntersectionObserver | null = null;
    if (oscilloscopeRef.current) {
      observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            // Component is visible, recalculate scale
            setTimeout(updateScale, 100);
          }
        });
      }, { threshold: 0.1 });
      observer.observe(oscilloscopeRef.current);
    }
    
    return () => {
      clearTimeout(timer1);
      clearTimeout(timer2);
      clearTimeout(timer3);
      if (observer) {
        observer.disconnect();
      }
    };
  }, [oscilloscopeWidth, events.length, timeRange]);

  return (
    <div 
      className="status-timeline"
      onClick={(e) => e.stopPropagation()}
    >
      <div className="terminal-box-header pane-terminal-header">
        <div className="terminal-box-top">
          <div className="terminal-box-title-row pane-terminal-title-row">
            <span className="pane-terminal-title-start">┌─ STATUS TIMELINE</span>
            <span className="pane-terminal-title-fill" aria-hidden>
              {TERMINAL_RULE_FILL}
            </span>
            <div className="pane-header-right-actions">
              <PollingStatusLight
                lastUpdatedAt={statusLightLastUpdatedAt}
                expectedIntervalMs={60_000}
                ariaLabel="Status timeline data freshness"
              />
            </div>
            <span className="pane-terminal-title-corner">┐</span>
          </div>
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
        {isBetaMode && (
          <button
            className={`time-range-btn ${colorMode ? 'active' : ''}`}
            onClick={() => setColorMode(!colorMode)}
            title="Toggle color-coded trace"
          >
            [COLOR]
          </button>
        )}
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
                  <div
                    style={{
                      transform: `scaleX(${scaleX > 0 && !isNaN(scaleX) ? scaleX : 1})`,
                      transformOrigin: 'left center',
                      width: '100%',
                      height: '100%',
                      minHeight: '150px',
                      willChange: 'auto',
                      backfaceVisibility: 'hidden',
                    }}
                  >
                    <svg 
                      className="oscilloscope-svg"
                      viewBox="0 0 100 100"
                      preserveAspectRatio="none"
                      shapeRendering="crispEdges"
                      style={{ 
                        imageRendering: 'crisp-edges' as const,
                        filter: 'none',
                      }}
                    >
                    {/* Grid lines for each status level */}
                    {statusLevels.map((level, idx) => {
                      const levelY = (1 - level / 4) * 100; // Invert Y (0 = bottom, 4 = top)
                      const paddedY = 8 + (levelY / 100) * 84; // Map to 8-92 range
                      return (
                        <line 
                          key={idx}
                          x1="0" 
                          y1={paddedY} 
                          x2="100" 
                          y2={paddedY}
                          stroke="var(--color-text-dim)"
                          strokeWidth="0.5"
                          opacity="0.3"
                          shapeRendering="crispEdges"
                          style={{ filter: 'none' }}
                        />
                      );
                    })}
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
                    {/* Oscilloscope trace - digital step (right-angle transitions) */}
                    {svgPoints.length > 0 && (svgPoints.length > 1 ? (colorMode && isBetaMode ? (
                      // Color mode: one path segment per status run, colored by status level
                      (() => {
                        const segments: Array<{ d: string; color: string }> = [];
                        let currentPath = `M ${svgPoints[0].x},${svgPoints[0].y}`;
                        let currentColor = getColorForY(svgPoints[0].y);

                        for (let i = 1; i < svgPoints.length; i++) {
                          const prev = svgPoints[i - 1];
                          const curr = svgPoints[i];
                          const nextColor = getColorForY(curr.y);

                          // Horizontal step at outgoing status Y
                          currentPath += ` L ${curr.x},${prev.y}`;

                          if (nextColor !== currentColor) {
                            segments.push({ d: currentPath, color: currentColor });
                            // Vertical drop in new color
                            currentPath = `M ${curr.x},${prev.y} L ${curr.x},${curr.y}`;
                            currentColor = nextColor;
                          } else {
                            // Same color — continue with vertical
                            currentPath += ` L ${curr.x},${curr.y}`;
                          }
                        }

                        if (currentPath) {
                          segments.push({ d: currentPath, color: currentColor });
                        }

                        return segments.map((segment, idx) => (
                          <path
                            key={`trace-segment-${idx}`}
                            d={segment.d}
                            fill="none"
                            stroke={segment.color}
                            strokeWidth="2"
                            strokeLinecap="butt"
                            strokeLinejoin="miter"
                            vectorEffect="non-scaling-stroke"
                            shapeRendering="crispEdges"
                            style={{ filter: 'none' }}
                          />
                        ));
                      })()
                    ) : (
                      // Normal mode: single digital step path
                      <path
                        d={(() => {
                          // Step path: horizontal to next X at current Y, then vertical to next Y
                          let pathD = `M ${svgPoints[0].x},${svgPoints[0].y}`;
                          for (let i = 1; i < svgPoints.length; i++) {
                            const prev = svgPoints[i - 1];
                            const curr = svgPoints[i];
                            pathD += ` L ${curr.x},${prev.y} L ${curr.x},${curr.y}`;
                          }
                          return pathD;
                        })()}
                        fill="none"
                        stroke="var(--color-text-primary)"
                        strokeWidth="2"
                        strokeLinecap="butt"
                        strokeLinejoin="miter"
                        vectorEffect="non-scaling-stroke"
                        shapeRendering="crispEdges"
                        style={{ filter: 'none' }}
                        className="oscilloscope-trace"
                      />
                    )) : (
                      // Single point - render only at that time (no line across full width; we don't assume state elsewhere)
                      <circle
                        cx={svgPoints[0].x}
                        cy={svgPoints[0].y}
                        r="2"
                        fill="var(--color-text-primary)"
                        stroke="none"
                        className="oscilloscope-trace"
                      />
                    ))}
                    {/* Timestamp markers - vertical lines */}
                    {oscilloscopeData.map((dataPoint, dataIdx) => {
                      const x = (dataPoint.time / 100) * 100;
                      const timestamp = new Date(startTime.getTime() + (dataPoint.time / 100) * totalDuration);
                      const hoverRadius = 0.5; // Extend hover area by 0.5% on each side
                      
                      return (
                        <g key={dataIdx}>
                          {/* Invisible wider rectangle for easier hover */}
                          <rect
                            x={x - hoverRadius}
                            y="0"
                            width={hoverRadius * 2}
                            height="100"
                            fill="transparent"
                            className="oscilloscope-timestamp-hover-area"
                            onMouseEnter={(e) => {
                              const rect = e.currentTarget.getBoundingClientRect();
                              const containerRect = e.currentTarget.closest('.oscilloscope-display')?.getBoundingClientRect();
                              if (containerRect) {
                                const normalized = normalizeStatus(dataPoint.status, isOnline);
                                const levelY = (1 - (STATUS_LEVELS[normalized] ?? 3) / 4) * 100;
                                const paddedY = 8 + (levelY / 100) * 84; // Map to 8-92 range
                                // Get error, heartbeat flag, and latest (rightmost/current) from dataPoint
                                setHoveredPoint({
                                  x: x,
                                  y: paddedY,
                                  status: normalized.toUpperCase(),
                                  timestamp: timestamp,
                                  error: dataPoint.error,
                                  is_heartbeat: dataPoint.is_heartbeat,
                                  isLatest: dataIdx === oscilloscopeData.length - 1,
                                });
                                
                                const tooltipWidth = 250; // Wider to accommodate error messages
                                const hasError = dataPoint.error && dataPoint.error.length > 0;
                                // Height: label (20px) + status (20px) + timestamp (20px) + error (if present, 20px)
                                const tooltipHeight = hasError ? 80 : 60; // Account for heartbeat/event label
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
                            className="oscilloscope-timestamp-line"
                            data-timestamp-idx={dataIdx}
                            pointerEvents="none"
                            style={{ filter: 'none' }}
                          />
                        </g>
                      );
                    })}
                    {/* Alarm dots (mapped along ERROR row) */}
                    {alarmEvents.map((alarm, idx) => {
                      const alarmTime = new Date(alarm.time).getTime();
                      if (alarmTime < startTime.getTime() || alarmTime > _endTime.getTime()) {
                        return null;
                      }
                      const relative = ((alarmTime - startTime.getTime()) / totalDuration) * 100;
                      const errorLevel = STATUS_LEVELS['error'] ?? 1;
                      const levelY = (1 - errorLevel / 4) * 100;
                      const paddedY = 8 + (levelY / 100) * 84;
                      return (
                        <circle
                          key={`alarm-dot-${idx}`}
                          cx={relative}
                          cy={paddedY}
                          r="1.5"
                          fill="var(--color-error)"
                          stroke="none"
                        />
                      );
                    })}
                    {/* Part count dots (mapped along OPERATING row, one per cycle, size by part_count) */}
                    {cycleEntries.map((cycle, idx) => {
                      if (!cycle.part_count || cycle.part_count <= 0) {
                        return null;
                      }
                      const endMs = new Date(cycle.end_time || cycle.start_time).getTime();
                      if (endMs < startTime.getTime() || endMs > _endTime.getTime()) {
                        return null;
                      }
                      const relative = ((endMs - startTime.getTime()) / totalDuration) * 100;
                      const opLevel = STATUS_LEVELS['operating'] ?? 4;
                      const levelY = (1 - opLevel / 4) * 100;
                      const paddedY = 8 + (levelY / 100) * 84;
                      const radius = Math.min(3, 1 + Math.log10(cycle.part_count + 1));
                      return (
                        <circle
                          key={`part-dot-${idx}`}
                          cx={relative}
                          cy={paddedY}
                          r={radius}
                          fill="var(--color-accent, #00bcd4)"
                          stroke="none"
                        />
                      );
                    })}
                    </svg>
                  </div>
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
                {hoveredPoint.isLatest ? '[LATEST]' : (hoveredPoint.is_heartbeat ? '[HEARTBEAT]' : '[STATUS EVENT]')}<br/>
                {hoveredPoint.status}<br/>
                {hoveredPoint.timestamp.toLocaleString()}
                {hoveredPoint.error && (
                  <>
                    <br/>
                    <span style={{ color: 'var(--color-error)', fontSize: '0.9em' }}>
                      {hoveredPoint.error}
                    </span>
                  </>
                )}
              </div>
            )}
            <div className="oscilloscope-x-axis">
              <span className="oscilloscope-x-label-start">{axisEnds.left}</span>
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
              <div className="oscilloscope-x-axis-endgroup">
                <span className="oscilloscope-x-label-end">{axisEnds.right}</span>
                <ChartTimeAxisToggle
                  timeAxisMode={timeAxisMode}
                  toggleTimeAxisMode={toggleTimeAxisMode}
                />
              </div>
            </div>
          </div>
        )}
      </div>
      <div className="terminal-box-footer pane-terminal-footer">
        <div className="pane-terminal-footer-row">
          <span className="pane-terminal-footer-corner">└</span>
          <span className="pane-terminal-footer-fill" aria-hidden>
            {TERMINAL_RULE_FILL}
          </span>
          <span className="pane-terminal-footer-corner">┘</span>
        </div>
      </div>
    </div>
  );
};

