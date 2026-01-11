import React, { useState, useEffect } from 'react';
import { createPortal } from 'react-dom';
import './AlarmPane.css';

interface Alarm {
  code: string;
  message: string;
  description?: string;
  severity?: string;
  level_class?: string;
  stop_level?: string;
  reset_level?: string;
  cause?: string;
  solution?: string;
  time?: string;
}

interface AlarmPaneProps {
  machineId: number;
  currentAlarms?: Array<{
    code: string;
    message: string;
    description?: string;
    severity?: string;
    level_class?: string;
    stop_level?: string;
    reset_level?: string;
    cause?: string;
    solution?: string;
  }>;
  onExpand?: () => void;
  isExpanded?: boolean;
}

export const AlarmPane: React.FC<AlarmPaneProps> = ({ machineId: _machineId, currentAlarms, onExpand, isExpanded = false }) => {
  const [alarms, setAlarms] = useState<Alarm[]>([]);
  const [loading, setLoading] = useState(false);
  const [hoveredAlarm, setHoveredAlarm] = useState<Alarm | null>(null);
  const [tooltipPosition, setTooltipPosition] = useState<{ x: number; y: number } | null>(null);

  // Update from WebSocket data - websocket always provides alarms (even if empty array)
  useEffect(() => {
    if (currentAlarms !== undefined) {
      // Always update from prop, even if empty array (handles alarm clearing)
      const mappedAlarms = Array.isArray(currentAlarms) 
        ? currentAlarms.map(a => ({
            code: a.code,
            message: a.message,
            description: a.description,
            severity: a.severity,
            level_class: a.level_class,
            stop_level: a.stop_level,
            reset_level: a.reset_level,
            cause: a.cause,
            solution: a.solution,
          }))
        : [];
      setAlarms(mappedAlarms);
      setLoading(false);
    } else {
      // If currentAlarms is undefined, show empty state (websocket will provide data soon)
      setAlarms([]);
      setLoading(false);
    }
  }, [currentAlarms]);

  const getSeverityLevel = (alarm: Alarm): number => {
    // Use stop_level exclusively (higher number = more severe)
    // Stop levels: 5 = most critical, 4 = critical, 3 = error, 2 = warning, 1 = info
    if (alarm.stop_level !== undefined && alarm.stop_level !== null && alarm.stop_level !== '') {
      const level = parseInt(String(alarm.stop_level), 10);
      if (!isNaN(level) && level >= 1 && level <= 5) {
        return level;
      }
    }
    
    // If stop_level is missing or invalid, default to 3 (error level)
    // This should rarely happen if the API is working correctly
    return 3;
  };

  const getSeverityColor = (alarm: Alarm): string => {
    const level = getSeverityLevel(alarm);
    
    // Map severity level to color
    // Level 5: Critical (bright red)
    if (level >= 5) return '#ff0000';
    // Level 4: Critical (red)
    if (level === 4) return '#ff3333';
    // Level 3: Error (red-orange)
    if (level === 3) return '#ff6600';
    // Level 2: Warning (orange/yellow)
    if (level === 2) return '#ffaa00';
    // Level 1: Info (cyan)
    if (level === 1) return '#00ffff';
    
    // Default: red for unknown
    return '#ff0000';
  };

  const getSeverityIndicator = (alarm: Alarm) => {
    const level = getSeverityLevel(alarm);
    if (level >= 5) return '!!!';
    if (level === 4) return '!!!';
    if (level === 3) return '!!';
    if (level === 2) return '!';
    return '!';
  };

  // Sort alarms by severity (highest first) using stop_level
  const sortedAlarms = [...alarms].sort((a, b) => {
    const levelA = getSeverityLevel(a);
    const levelB = getSeverityLevel(b);
    return levelB - levelA; // Higher severity first
  });

  // Split alarms: highest severity (stop_level 4-5) vs others (stop_level 1-3)
  // Highest severity alarms go in left column, others in right column
  const highestSeverityAlarms = sortedAlarms.filter(a => getSeverityLevel(a) >= 4);
  const otherAlarms = sortedAlarms.filter(a => getSeverityLevel(a) < 4);

  // Show all alarms when expanded, otherwise limit to 10 per column
  const maxPerColumn = isExpanded ? Infinity : 10;
  const visibleHighest = isExpanded ? highestSeverityAlarms : highestSeverityAlarms.slice(0, maxPerColumn);
  const visibleOthers = isExpanded ? otherAlarms : otherAlarms.slice(0, maxPerColumn);
  const hasMoreHighest = !isExpanded && highestSeverityAlarms.length > maxPerColumn;
  const hasMoreOthers = !isExpanded && otherAlarms.length > maxPerColumn;
  const hasMoreAlarms = hasMoreHighest || hasMoreOthers;

  return (
    <div 
      className="alarm-pane terminal-box"
      onClick={(e) => e.stopPropagation()}
    >
      <div className="terminal-box-header">
        <div className="terminal-box-top">
          <div className="terminal-box-title-row">
            <span>┌─ ALARMS ({alarms.length}) {'─'.repeat(Math.max(0, 40 - 10 - String(alarms.length).length))}</span>
            {hasMoreAlarms && onExpand && (
              <button 
                className="expand-toggle"
                onClick={(e) => {
                  e.stopPropagation();
                  onExpand();
                }}
                title="Expand"
              >
                [EXPAND]
              </button>
            )}
            <span>┐</span>
          </div>
        </div>
      </div>
      <div className="terminal-box-content">
        {loading ? (
          <div className="alarm-loading">LOADING...</div>
        ) : !Array.isArray(alarms) || alarms.length === 0 ? (
          <div className="alarm-empty">NO ACTIVE ALARMS</div>
        ) : (
          <div className="alarm-list-grid">
            {/* Highest Severity Column (Level 4-5) */}
            <div className="alarm-column">
              {visibleHighest.length > 0 ? (
                visibleHighest.map((alarm, idx) => {
                  const severityColor = getSeverityColor(alarm);
                  const displayText = alarm.description || alarm.message || alarm.code;
                  return (
                    <div key={idx} className="alarm-item">
                      <div 
                        className="alarm-item-header"
                        style={{ color: severityColor, '--alarm-color': severityColor } as React.CSSProperties}
                      >
                        <span className="alarm-severity" style={{ color: severityColor }}>
                          {getSeverityIndicator(alarm)}
                        </span>
                        <span 
                          className="alarm-code" 
                          style={{ 
                            color: severityColor, 
                            cursor: (alarm.cause || alarm.solution) ? 'help' : 'default' 
                          }}
                          onMouseEnter={(e) => {
                            if (alarm.cause || alarm.solution) {
                              const rect = e.currentTarget.getBoundingClientRect();
                              setHoveredAlarm(alarm);
                              // Position tooltip above the alarm code, centered
                              // Adjust if tooltip would go off-screen
                              const tooltipWidth = 300; // Approximate tooltip width
                              let x = rect.left + rect.width / 2;
                              const minX = tooltipWidth / 2;
                              const maxX = window.innerWidth - tooltipWidth / 2;
                              x = Math.max(minX, Math.min(maxX, x));
                              
                              setTooltipPosition({
                                x: x,
                                y: rect.top,
                              });
                            }
                          }}
                          onMouseLeave={() => {
                            setHoveredAlarm(null);
                            setTooltipPosition(null);
                          }}
                        >
                          {alarm.code}
                        </span>
                        <span className="alarm-message-inline" style={{ color: severityColor }}>{displayText}</span>
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="alarm-column-empty">NO CRITICAL ALARMS</div>
              )}
              {hasMoreHighest && onExpand && (
                <div 
                  className="alarm-more" 
                  onClick={(e) => {
                    e.stopPropagation();
                    onExpand();
                  }}
                  style={{ cursor: 'pointer' }}
                >
                  +{highestSeverityAlarms.length - maxPerColumn} MORE
                </div>
              )}
            </div>

            {/* Other Alarms Column (Level 1-3) */}
            <div className="alarm-column">
              {visibleOthers.length > 0 ? (
                visibleOthers.map((alarm, idx) => {
                  const severityColor = getSeverityColor(alarm);
                  const displayText = alarm.description || alarm.message || alarm.code;
                  return (
                    <div key={idx} className="alarm-item">
                      <div 
                        className="alarm-item-header"
                        style={{ color: severityColor, '--alarm-color': severityColor } as React.CSSProperties}
                      >
                        <span className="alarm-severity" style={{ color: severityColor }}>
                          {getSeverityIndicator(alarm)}
                        </span>
                        <span 
                          className="alarm-code" 
                          style={{ 
                            color: severityColor, 
                            cursor: (alarm.cause || alarm.solution) ? 'help' : 'default' 
                          }}
                          onMouseEnter={(e) => {
                            if (alarm.cause || alarm.solution) {
                              const rect = e.currentTarget.getBoundingClientRect();
                              setHoveredAlarm(alarm);
                              // Position tooltip above the alarm code, centered
                              // Adjust if tooltip would go off-screen
                              const tooltipWidth = 300; // Approximate tooltip width
                              let x = rect.left + rect.width / 2;
                              const minX = tooltipWidth / 2;
                              const maxX = window.innerWidth - tooltipWidth / 2;
                              x = Math.max(minX, Math.min(maxX, x));
                              
                              setTooltipPosition({
                                x: x,
                                y: rect.top,
                              });
                            }
                          }}
                          onMouseLeave={() => {
                            setHoveredAlarm(null);
                            setTooltipPosition(null);
                          }}
                        >
                          {alarm.code}
                        </span>
                        <span className="alarm-message-inline" style={{ color: severityColor }}>{displayText}</span>
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="alarm-column-empty">NO WARNING/INFO ALARMS</div>
              )}
              {hasMoreOthers && onExpand && (
                <div 
                  className="alarm-more" 
                  onClick={(e) => {
                    e.stopPropagation();
                    onExpand();
                  }}
                  style={{ cursor: 'pointer' }}
                >
                  +{otherAlarms.length - maxPerColumn} MORE
                </div>
              )}
            </div>
          </div>
        )}
      </div>
      <div className="terminal-box-footer">
        └{'─'.repeat(42)}┘
      </div>
      
      {/* Alarm Code Tooltip - Rendered via Portal to avoid clipping */}
      {hoveredAlarm && tooltipPosition && (hoveredAlarm.cause || hoveredAlarm.solution) && typeof document !== 'undefined' && createPortal(
        <div
          className="alarm-code-tooltip"
          style={{
            position: 'fixed',
            left: `${tooltipPosition.x}px`,
            top: `${tooltipPosition.y}px`,
            transform: 'translate(-50%, calc(-100% - 8px))',
            zIndex: 10000,
          }}
          onMouseEnter={() => {
            // Keep tooltip visible when hovering over it
          }}
          onMouseLeave={() => {
            setHoveredAlarm(null);
            setTooltipPosition(null);
          }}
        >
          <div className="alarm-tooltip-content">
            {hoveredAlarm.cause && (
              <div className="alarm-tooltip-section">
                <div className="alarm-tooltip-label">CAUSE:</div>
                <div className="alarm-tooltip-text">{hoveredAlarm.cause}</div>
              </div>
            )}
            {hoveredAlarm.solution && (
              <div className="alarm-tooltip-section">
                <div className="alarm-tooltip-label">SOLUTION:</div>
                <div className="alarm-tooltip-text">{hoveredAlarm.solution}</div>
              </div>
            )}
          </div>
        </div>,
        document.body
      )}
    </div>
  );
};

