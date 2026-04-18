import React from 'react';
import { PollingStatusLight } from '../ui/PollingStatusLight';
import { PaneTerminalFooter, PaneTerminalHeader } from './PaneTerminalChrome';
import './PanelPane.css';

/** CNC panel poll payload (doors, mode/screen, overrides). Reused by overview mini panel. */
export interface PanelData {
  doors?: {
    outer_door?: number;
    inner_door?: number;
    side_door?: number;
  };
  mode_and_functions?: {
    mode?: number;
    screen?: number;
    block_skip?: number;
    opt_stop?: number;
    single_block?: number;
    dry_run?: number;
    machine_lock?: number;
    coolant_pump?: number;
    chip_shower?: number;
    machine_light?: number;
    pallet_select_key?: number;
    table_light?: number;
    door_unlock_1?: number;
    door_unlock_2?: number;
  };
  overrides?: {
    rapid_traverse_override?: number;
    feedrate_override?: number;
    spindle_override?: number;
    emergency_stop?: number;
    door_interlock?: number;
    door_interlock_mode_right?: number;
    door_interlock_mode_left?: number;
    data_protection?: number;
    enable?: number;
    master_on?: number;
  };
  control_version?: string;
}

interface PanelPaneProps {
  panelData?: PanelData | null;
  onExpand?: () => void;
  pollTimestamp?: string | null;
  pollIntervalSeconds?: number;
}

const MODE_LABELS: { [key: number]: string } = {
  0: 'MANUAL',
  1: 'MDI',
  2: 'MEMORY',
  3: 'EDIT',
  4: 'MDI MANUAL',
  5: 'OP EDIT',
};

const SCREEN_LABELS: { [key: number]: string } = {
  0: 'OFF',
  1: 'ALARM',
  2: 'DATA BANK',
  3: 'ATC',
  4: 'PROGRAM',
  5: 'MANUAL',
  6: 'POSITION',
  7: 'I/O',
  8: 'MONITOR',
  9: 'GRAPH',
};

// LED Indicator Component
const LED: React.FC<{ on: boolean; label: string; color?: string; statusText?: string }> = ({ on, label, color = '#00ff00', statusText }) => {
  const displayStatus = statusText !== undefined ? statusText : (on ? 'ON' : 'OFF');
  const statusClass = statusText !== undefined 
    ? (statusText === 'OPEN' ? 'led-status-on' : statusText === 'CLOSED' ? 'led-status-on' : (on ? 'led-status-on' : 'led-status-off'))
    : (on ? 'led-status-on' : 'led-status-off');
  
  return (
    <div className="led-indicator">
      <div className="led-label">{label}</div>
      <div className={`led ${on ? 'led-on' : 'led-off'}`} style={{ '--led-color': color } as React.CSSProperties}>
        <div className="led-glow"></div>
        <div className="led-inner"></div>
      </div>
      <div className={`led-status ${statusClass}`}>{displayStatus}</div>
    </div>
  );
};

// ASCII Vertical Slider Component (like audio mixer)
const VerticalSlider: React.FC<{ 
  value: number; 
  label: string; 
  segments?: number; // Total number of segments (20 = 10 for 0-100%, 10 for 100-200%)
}> = ({ 
  value, 
  label, 
  segments = 20
}) => {
  const isProhibited = value === 999;
  
  // Percentage value (can be 0-200%)
  const percentage = value;
  const isExact100 = percentage === 100;
  const isOver100 = percentage > 100;
  
  // Value text for display box
  const valueText = isProhibited ? 'XXX' : value.toString().padStart(3, '0');
  
  // Calculate which segments should be filled
  // 20 segments total: segments 1-10 = 0-100% (10% each), segments 11-20 = 100-200% (10% each)
  const segmentSize = 10; // 10% per segment (20 segments for 0-200%)
  const segmentsPer100 = segments / 2; // 10 segments for 0-100%
  const filledSegments = isProhibited ? 0 : Math.min(Math.ceil(percentage / segmentSize), segments);
  
  // Determine overall color for value box - match highest filled segment color
  let valueBoxColor = 'grey';
  if (isProhibited) {
    valueBoxColor = 'red';
  } else if (filledSegments > segmentsPer100) {
    // Above 100% - topmost segment is red (in 100-200% range)
    valueBoxColor = 'red';
  } else if (filledSegments === segmentsPer100) {
    // Exactly 100% - all segments green
    valueBoxColor = 'green';
  } else if (filledSegments >= segmentsPer100 * 0.75) {
    // 75%+ - all segments yellow
    valueBoxColor = 'yellow';
  } else if (filledSegments >= segmentsPer100 * 0.5) {
    // 50%+ - all segments orange
    valueBoxColor = 'orange';
  } else {
    // < 50% - all segments grey
    valueBoxColor = 'grey';
  }
  
  return (
    <div className="vertical-slider-ascii">
      <div className="slider-label">{label}</div>
      <div className="slider-track-ascii slider-track-long">
        {/* Build slider from top to bottom (segments) */}
        {Array.from({ length: segments }, (_, i) => {
          const segmentNum = segments - i; // Count from top (segment 20, 19, 18, ..., 1)
          const isFilled = segmentNum <= filledSegments;
          
          // Determine per-segment color based on level
          let segmentColor = 'grey';
          if (isFilled) {
            if (segmentNum <= segmentsPer100) {
              // Segments 1-10: 0-100% range
              if (isExact100) {
                // At exactly 100%, all segments green
                segmentColor = 'green';
              } else if (isOver100) {
                // Above 100%, all 0-100% segments green
                segmentColor = 'green';
              } else {
                // Below 100%, all filled segments same color based on level (like rapid)
                const filledInRange = Math.min(filledSegments, segmentsPer100);
                if (filledInRange === segmentsPer100) {
                  segmentColor = 'green'; // 100%
                } else if (filledInRange >= segmentsPer100 * 0.75) {
                  segmentColor = 'yellow'; // 75%+
                } else if (filledInRange >= segmentsPer100 * 0.5) {
                  segmentColor = 'orange'; // 50%+
                } else {
                  segmentColor = 'grey'; // < 50%
                }
              }
            } else {
              // Segments 11-20: 100-200% range - always red when filled
              segmentColor = 'red';
            }
          }
          
          // Add subtle random brightness variation for analog noise effect (like old transistor radio)
          // Use hash-like function for pseudo-random but consistent variation per segment
          const hash = (segmentNum * 73 + 37) % 97; // Simple hash for pseudo-randomness
          const brightnessVariation = 0.96 + (hash / 97) * 0.04; // Very subtle: 96% to 100%
          
          return (
            <div 
              key={segmentNum} 
              className={`slider-segment slider-segment-${segmentColor} ${isFilled ? 'filled' : ''}`}
              style={isFilled ? { opacity: brightnessVariation, filter: `brightness(${brightnessVariation})` } : undefined}
            >
              {isFilled ? '▓█▓' : '░░░'}
            </div>
          );
        })}
      </div>
      <div className={`slider-value-box slider-value-${valueBoxColor}`}>
        {valueText}
      </div>
    </div>
  );
};

// Rapid Traverse Slider (uses 20 segments: 0%, 25%, 50%, 75%, 100% fill 0, 5, 10, 15, 20 segments)
const RapidTraverseSlider: React.FC<{ 
  value: number;
}> = ({ 
  value 
}) => {
  const isProhibited = value === 9;
  const segments = 20; // 20 segments, same as feed/spindle
  
  // Rapid traverse: 0 = 0%, 1 = 25%, 2 = 50%, 3 = 75%, 4 = 100%, 5 = 0%, 9 = prohibited
  let displayValue: string;
  let filledSegments: number = 0;
  
  if (isProhibited) {
    displayValue = 'XXX';
    filledSegments = 0;
  } else if (value === 0 || value === 5) {
    displayValue = '000';
    filledSegments = 0; // 0% - no segments
  } else if (value === 1) {
    displayValue = '001';
    filledSegments = 5; // 25% - 5 segments out of 20
  } else if (value === 2) {
    displayValue = '002';
    filledSegments = 10; // 50% - 10 segments out of 20
  } else if (value === 3) {
    displayValue = '003';
    filledSegments = 15; // 75% - 15 segments out of 20
  } else if (value === 4) {
    displayValue = '100';
    filledSegments = 20; // 100% - all 20 segments
  } else {
    displayValue = '000';
    filledSegments = 0;
  }
  
  // Determine overall color for value box - match segment colors
  let valueBoxColor = 'grey';
  if (isProhibited) {
    valueBoxColor = 'red';
  } else if (filledSegments === segments) {
    valueBoxColor = 'green'; // 100% = green
  } else if (filledSegments >= segments * 0.75) {
    valueBoxColor = 'yellow'; // 75%+ = yellow
  } else if (filledSegments >= segments * 0.5) {
    valueBoxColor = 'orange'; // 50%+ = orange
  } else {
    valueBoxColor = 'grey'; // < 50% = grey
  }
  
  return (
    <div className="vertical-slider-ascii">
      <div className="slider-label">RAPID</div>
      <div className="slider-track-ascii slider-track-long">
        {/* Build slider from top to bottom (20 segments, same height as feed/spindle) */}
        {Array.from({ length: segments }, (_, i) => {
          const segmentNum = segments - i; // Count from top (segment 20, 19, 18, ..., 1)
          const isFilled = segmentNum <= filledSegments;
          
          // Determine per-segment color: all filled segments same color based on level
          let segmentColor = 'grey';
          if (isFilled) {
            if (filledSegments === segments) {
              // 100% - all segments green
              segmentColor = 'green';
            } else if (filledSegments >= segments * 0.75) {
              // 75%+ - all segments yellow
              segmentColor = 'yellow';
            } else if (filledSegments >= segments * 0.5) {
              // 50%+ - all segments orange
              segmentColor = 'orange';
            } else {
              // < 50% - all segments grey
              segmentColor = 'grey';
            }
          }
          
          // Add subtle random brightness variation for analog noise effect (like old transistor radio)
          // Use hash-like function for pseudo-random but consistent variation per segment
          const hash = (segmentNum * 73 + 37) % 97; // Simple hash for pseudo-randomness
          const brightnessVariation = 0.96 + (hash / 97) * 0.04; // Very subtle: 96% to 100%
          
          return (
            <div 
              key={segmentNum} 
              className={`slider-segment slider-segment-${segmentColor} ${isFilled ? 'filled' : ''}`}
              style={isFilled ? { opacity: brightnessVariation, filter: `brightness(${brightnessVariation})` } : undefined}
            >
              {isFilled ? '▓█▓' : '░░░'}
            </div>
          );
        })}
      </div>
      <div className={`slider-value-box slider-value-${valueBoxColor}`}>
        {displayValue}
      </div>
    </div>
  );
};

export const PanelPane: React.FC<PanelPaneProps> = ({
  panelData,
  pollTimestamp,
  pollIntervalSeconds = 5,
}) => {
  const pollMs = Math.max((pollIntervalSeconds ?? 5) * 1000, 1000);

  const panelTitleHeader = (
    <PaneTerminalHeader label="PANEL STATUS">
      <PollingStatusLight
        lastUpdatedAt={pollTimestamp}
        expectedIntervalMs={pollMs}
        ariaLabel="Panel status data freshness"
      />
    </PaneTerminalHeader>
  );

  if (!panelData) {
    return (
      <div className="panel-pane">
        <div className="terminal-box">
          {panelTitleHeader}
          <div className="terminal-box-content">
            <div className="panel-empty">NO PANEL DATA AVAILABLE</div>
          </div>
        </div>
      </div>
    );
  }

  const doors = panelData.doors || {};
  const modeFunc = panelData.mode_and_functions || {};
  const overrides = panelData.overrides || {};

  // Determine LED colors based on state
  const getDoorLEDColor = (state?: number) => {
    if (state === undefined) return '#666666';
    return state === 1 ? '#ff0000' : '#00ff00'; // Red for open (1), green for closed (0)
  };

  // Get door state label and status text
  const getDoorLabel = (doorType: string) => {
    return doorType;
  };

  const getDoorStatusText = (state?: number) => {
    if (state === undefined) return 'UNKNOWN';
    return state === 1 ? 'OPEN' : 'CLOSED';
  };

  const getSwitchLEDColor = (state?: number) => {
    if (state === undefined) return '#666666';
    return state === 1 ? '#00ff00' : '#333333'; // Green for ON
  };

  const getEmergencyStopLEDColor = (state?: number) => {
    if (state === undefined) return '#666666';
    // Emergency stop: 0 = ON (red), 1 = OFF (green)
    return state === 0 ? '#ff0000' : '#00ff00';
  };

  return (
    <div className="panel-pane">
      <div className="terminal-box">
        {panelTitleHeader}
        <div className="terminal-box-content">
          {/* Doors & System Status Section (Combined) */}
          <div className="panel-section">
            <div className="panel-section-title">DOORS & SYSTEM STATUS</div>
            
            <div className="panel-subsection">
              <div className="panel-subsection-title">DOORS</div>
              <div className="led-group">
                <LED 
                  on={doors.outer_door !== undefined} 
                  label={getDoorLabel("OUTER")}
                  color={getDoorLEDColor(doors.outer_door)}
                  statusText={getDoorStatusText(doors.outer_door)}
                />
                <LED 
                  on={doors.inner_door !== undefined} 
                  label={getDoorLabel("INNER")}
                  color={getDoorLEDColor(doors.inner_door)}
                  statusText={getDoorStatusText(doors.inner_door)}
                />
                <LED 
                  on={doors.side_door !== undefined} 
                  label={getDoorLabel("SIDE")}
                  color={getDoorLEDColor(doors.side_door)}
                  statusText={getDoorStatusText(doors.side_door)}
                />
              </div>
            </div>
            
            <div className="led-group-separator"></div>
            
            <div className="panel-subsection">
              <div className="panel-subsection-title">SYSTEM STATUS</div>
              <div className="led-group">
                <LED 
                  on={overrides.emergency_stop === 0} 
                  label="E-STOP" 
                  color={getEmergencyStopLEDColor(overrides.emergency_stop)}
                />
                {overrides.door_interlock !== undefined && (
                  <LED 
                    on={overrides.door_interlock === 1} 
                    label="DOOR IL" 
                    color={getSwitchLEDColor(overrides.door_interlock)}
                  />
                )}
                {overrides.door_interlock_mode_right !== undefined && (
                  <LED 
                    on={overrides.door_interlock_mode_right === 1} 
                    label="IL RIGHT" 
                    color={getSwitchLEDColor(overrides.door_interlock_mode_right)}
                  />
                )}
                {overrides.door_interlock_mode_left !== undefined && (
                  <LED 
                    on={overrides.door_interlock_mode_left === 1} 
                    label="IL LEFT" 
                    color={getSwitchLEDColor(overrides.door_interlock_mode_left)}
                  />
                )}
                <LED 
                  on={overrides.data_protection === 0} 
                  label="DATA PROT" 
                  color={overrides.data_protection === 0 ? '#ffaa00' : '#666666'}
                />
                {overrides.enable !== undefined && overrides.enable !== 0 && (
                  <LED 
                    on={true} 
                    label="ENABLE" 
                    color={getSwitchLEDColor(1)}
                  />
                )}
                <LED 
                  on={overrides.master_on === 1} 
                  label="MASTER ON" 
                  color={getSwitchLEDColor(overrides.master_on)}
                />
              </div>
            </div>
          </div>

          {/* Mode & Functions Section */}
          <div className="panel-section">
            <div className="panel-section-title">MODE & FUNCTIONS</div>
            <div className="panel-info-grid">
              <div className="info-item">
                <span className="info-label">MODE:</span>
                <span className="info-value">{MODE_LABELS[modeFunc.mode ?? -1] || 'UNKNOWN'}</span>
              </div>
              {modeFunc.screen !== undefined && (
                <div className="info-item">
                  <span className="info-label">SCREEN:</span>
                  <span className="info-value">{SCREEN_LABELS[modeFunc.screen] || 'UNKNOWN'}</span>
                </div>
              )}
            </div>
            <div className="led-group-separator" aria-hidden="true" />
            <div className="led-group led-group-switches">
              <LED 
                on={modeFunc.block_skip === 1} 
                label="BLK SKIP" 
                color={getSwitchLEDColor(modeFunc.block_skip)}
              />
              <LED 
                on={modeFunc.opt_stop === 1} 
                label="OPT STOP" 
                color={getSwitchLEDColor(modeFunc.opt_stop)}
              />
              <LED 
                on={modeFunc.single_block === 1} 
                label="SGL BLK" 
                color={getSwitchLEDColor(modeFunc.single_block)}
              />
              <LED 
                on={modeFunc.dry_run === 1} 
                label="DRY RUN" 
                color={getSwitchLEDColor(modeFunc.dry_run)}
              />
              <LED 
                on={modeFunc.machine_lock === 1} 
                label="MACH LOCK" 
                color={getSwitchLEDColor(modeFunc.machine_lock)}
              />
              <LED 
                on={modeFunc.coolant_pump === 1} 
                label="COOLANT" 
                color={getSwitchLEDColor(modeFunc.coolant_pump)}
              />
              <LED 
                on={modeFunc.chip_shower === 1} 
                label="SHOWER" 
                color={getSwitchLEDColor(modeFunc.chip_shower)}
              />
              <LED 
                on={modeFunc.machine_light === 1} 
                label="LIGHT" 
                color={getSwitchLEDColor(modeFunc.machine_light)}
              />
              {modeFunc.table_light !== undefined && (
                <LED 
                  on={modeFunc.table_light === 1} 
                  label="TBL LIGHT" 
                  color={getSwitchLEDColor(modeFunc.table_light)}
                />
              )}
              {modeFunc.door_unlock_1 !== undefined && (
                <LED 
                  on={modeFunc.door_unlock_1 === 1} 
                  label="UNLOCK 1" 
                  color={getSwitchLEDColor(modeFunc.door_unlock_1)}
                />
              )}
              {modeFunc.door_unlock_2 !== undefined && (
                <LED 
                  on={modeFunc.door_unlock_2 === 1} 
                  label="UNLOCK 2" 
                  color={getSwitchLEDColor(modeFunc.door_unlock_2)}
                />
              )}
            </div>
          </div>

          {/* Overrides Section */}
          <div className="panel-section panel-section-overrides">
            <div className="panel-section-title">OVERRIDES</div>
            <div className="slider-group">
              {overrides.rapid_traverse_override !== undefined && (
                <RapidTraverseSlider 
                  value={overrides.rapid_traverse_override}
                />
              )}
              {overrides.feedrate_override !== undefined && (
                <VerticalSlider 
                  value={overrides.feedrate_override}
                  label="FEED"
                  segments={20}
                />
              )}
              {overrides.spindle_override !== undefined && (
                <VerticalSlider 
                  value={overrides.spindle_override}
                  label="SPINDLE"
                  segments={20}
                />
              )}
            </div>
          </div>
        </div>
        <PaneTerminalFooter />
      </div>
    </div>
  );
};

