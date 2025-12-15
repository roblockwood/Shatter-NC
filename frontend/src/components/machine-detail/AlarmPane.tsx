import React, { useState, useEffect } from 'react';
import { API_BASE_URL } from '../../config/api';
import './AlarmPane.css';

interface Alarm {
  code: string;
  message: string;
  severity?: string;
  level_class?: string;
  time?: string;
}

interface AlarmPaneProps {
  machineId: number;
  currentAlarms?: Array<{ code: string; message: string; severity?: string; level_class?: string }>;
  onExpand?: () => void;
  isExpanded?: boolean;
}

export const AlarmPane: React.FC<AlarmPaneProps> = ({ machineId, currentAlarms, onExpand, isExpanded = false }) => {
  const [alarms, setAlarms] = useState<Alarm[]>([]);
  const [loading, setLoading] = useState(true);

  // Prioritize currentAlarms prop (from WebSocket) - update immediately when it changes
  useEffect(() => {
    if (currentAlarms !== undefined) {
      // Always update from prop, even if empty array (handles alarm clearing)
      const mappedAlarms = Array.isArray(currentAlarms) 
        ? currentAlarms.map(a => ({
            code: a.code,
            message: a.message,
            severity: a.severity,
            level_class: a.level_class,
          }))
        : [];
      setAlarms(mappedAlarms);
      setLoading(false);
      return; // Don't fetch if we have prop data
    }
  }, [currentAlarms]);

  // Only fetch from API if currentAlarms is not provided (fallback)
  useEffect(() => {
    // Skip fetch if we have currentAlarms prop (WebSocket data takes priority)
    if (currentAlarms !== undefined) {
      return;
    }

    const fetchAlarms = async () => {
      try {
        setLoading(true);
        const response = await fetch(`${API_BASE_URL}/api/machines/${machineId}/alarms?active_only=true`);
        if (response.ok) {
          const data = await response.json();
          // API returns { alarms: [...] } or just array
          const alarmArray = Array.isArray(data) ? data : (data.alarms || []);
          setAlarms(Array.isArray(alarmArray) ? alarmArray : []);
          
          // Debug: Log alarm severity data
          console.log('=== ALARM SEVERITY DEBUG ===');
          alarmArray.forEach((alarm: Alarm) => {
            console.log(`Code: ${alarm.code}, Severity: ${alarm.severity}, Level Class: ${alarm.level_class}`);
          });
          console.log('===========================');
        } else {
          setAlarms([]);
        }
      } catch (error) {
        console.error('Error fetching alarms:', error);
        setAlarms([]);
      } finally {
        setLoading(false);
      }
    };

    fetchAlarms();
    // Refresh every 30 seconds only if not using WebSocket data
    const interval = setInterval(fetchAlarms, 30000);
    return () => clearInterval(interval);
  }, [machineId, currentAlarms]);

  const getSeverityColor = (severity?: string, levelClass?: string): string => {
    // Priority: level_class > severity
    if (levelClass) {
      if (levelClass === 'alarm_level_4' || levelClass.includes('level_4') || levelClass.includes('critical')) {
        return '#ff0000'; // Red for critical
      }
      if (levelClass === 'alarm_level_3' || levelClass.includes('level_3') || levelClass.includes('error')) {
        return '#ff0000'; // Red for error
      }
      if (levelClass === 'alarm_level_2' || levelClass.includes('level_2') || levelClass.includes('warning')) {
        return '#ffaa00'; // Orange/Yellow for warning
      }
      if (levelClass === 'alarm_level_1' || levelClass.includes('level_1') || levelClass.includes('info')) {
        return '#00ffff'; // Cyan for info (distinct from default green)
      }
    }
    
    // Fallback to severity
    if (severity === 'critical') return '#ff0000';
    if (severity === 'error') return '#ff0000';
    if (severity === 'warning') return '#ffaa00';
    if (severity === 'info') return '#00ffff';
    
    // Default: use cyan to distinguish from terminal's default green
    return '#00ffff';
  };

  const getSeverityIndicator = (severity?: string, levelClass?: string) => {
    if (levelClass?.includes('level_4') || severity === 'critical') return '!!!';
    if (levelClass?.includes('level_3') || severity === 'error') return '!!';
    if (levelClass?.includes('level_2') || severity === 'warning') return '!';
    return '!';
  };

  const isInfoLevel = (severity?: string, levelClass?: string): boolean => {
    // Returns true for level 1 (info) only, false for levels 2/3/4
    if (levelClass) {
      // Check for exact level class matches first
      if (levelClass === 'alarm_level_1') {
        return true;
      }
      if (levelClass === 'alarm_level_2' || levelClass === 'alarm_level_3' || levelClass === 'alarm_level_4') {
        return false;
      }
      // Fallback to string includes for backwards compatibility
      if (levelClass.includes('level_1')) {
        return true;
      }
      if (levelClass.includes('level_2') || levelClass.includes('level_3') || levelClass.includes('level_4')) {
        return false;
      }
    }
    // Fallback to severity
    if (severity === 'info') return true;
    if (severity === 'warning' || severity === 'error' || severity === 'critical') return false;
    // If no level_class or severity, default to non-info (likely old data)
    return false;
  };

  // Split alarms: left pane = levels 2/3/4, right pane = level 1 (info) only
  const nonInfoAlarms = alarms.filter(a => !isInfoLevel(a.severity, a.level_class));
  const infoAlarms = alarms.filter(a => isInfoLevel(a.severity, a.level_class));

  // Show all alarms when expanded, otherwise limit to 10 per column
  const maxPerColumn = isExpanded ? Infinity : 10;
  const visibleNonInfo = isExpanded ? nonInfoAlarms : nonInfoAlarms.slice(0, maxPerColumn);
  const visibleInfo = isExpanded ? infoAlarms : infoAlarms.slice(0, maxPerColumn);
  const hasMoreNonInfo = !isExpanded && nonInfoAlarms.length > maxPerColumn;
  const hasMoreInfo = !isExpanded && infoAlarms.length > maxPerColumn;
  const hasMoreAlarms = hasMoreNonInfo || hasMoreInfo;

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
            {/* Non-Info Column (Levels 2/3/4) */}
            <div className="alarm-column">
              {visibleNonInfo.length > 0 ? (
                visibleNonInfo.map((alarm, idx) => {
                  const severityColor = getSeverityColor(alarm.severity, alarm.level_class);
                  return (
                    <div key={idx} className="alarm-item">
                      <div 
                        className="alarm-item-header"
                        style={{ color: severityColor, '--alarm-color': severityColor } as React.CSSProperties}
                      >
                        <span className="alarm-severity" style={{ color: severityColor }}>
                          {getSeverityIndicator(alarm.severity, alarm.level_class)}
                        </span>
                        <span className="alarm-code" style={{ color: severityColor }}>{alarm.code}</span>
                        <span className="alarm-message-inline" style={{ color: severityColor }}>{alarm.message}</span>
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="alarm-column-empty">NO WARNING/ERROR ALARMS</div>
              )}
              {hasMoreNonInfo && onExpand && (
                <div 
                  className="alarm-more" 
                  onClick={(e) => {
                    e.stopPropagation();
                    onExpand();
                  }}
                  style={{ cursor: 'pointer' }}
                >
                  +{nonInfoAlarms.length - maxPerColumn} MORE
                </div>
              )}
            </div>

            {/* Info Column (Level 1 only) */}
            <div className="alarm-column">
              {visibleInfo.length > 0 ? (
                visibleInfo.map((alarm, idx) => {
                  const severityColor = getSeverityColor(alarm.severity, alarm.level_class);
                  return (
                    <div key={idx} className="alarm-item">
                      <div 
                        className="alarm-item-header"
                        style={{ color: severityColor, '--alarm-color': severityColor } as React.CSSProperties}
                      >
                        <span className="alarm-severity" style={{ color: severityColor }}>
                          {getSeverityIndicator(alarm.severity, alarm.level_class)}
                        </span>
                        <span className="alarm-code" style={{ color: severityColor }}>{alarm.code}</span>
                        <span className="alarm-message-inline" style={{ color: severityColor }}>{alarm.message}</span>
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="alarm-column-empty">NO INFO ALARMS</div>
              )}
              {hasMoreInfo && onExpand && (
                <div 
                  className="alarm-more" 
                  onClick={(e) => {
                    e.stopPropagation();
                    onExpand();
                  }}
                  style={{ cursor: 'pointer' }}
                >
                  +{infoAlarms.length - maxPerColumn} MORE
                </div>
              )}
            </div>
          </div>
        )}
      </div>
      <div className="terminal-box-footer">
        └{'─'.repeat(42)}┘
      </div>
    </div>
  );
};

