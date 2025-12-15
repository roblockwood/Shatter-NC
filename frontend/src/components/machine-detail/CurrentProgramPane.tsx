import React, { useState, useEffect } from 'react';
import { API_BASE_URL } from '../../config/api';
import './CurrentProgramPane.css';

interface ToolValidation {
  tool_number: number;
  required_diameter: number;
  required_length: number;
  available: boolean;
  diameter_match: boolean;
  length_sufficient: boolean;
  machine_tool_data: {
    tool_name?: string;
    diameter?: number;
    length?: number;
  };
  warnings: string[];
  diameter_tolerance?: number;
  length_tolerance_plus?: number;
  length_tolerance_minus?: number;
}

interface WCSValidation {
  valid: boolean;
  work_offset: number;
  expected: {
    x: number;
    y: number;
    z: number;
  };
  actual: {
    x: number;
    y: number;
    z: number;
  };
  difference: {
    x: number;
    y: number;
    z: number;
  };
  tolerance: number;
  within_tolerance: boolean;
  warnings: string[];
}

interface Deployment {
  id: number;
  deployed_filename: string;
  deployed_at: string;
  deployed_path?: string;
  validation_passed?: boolean;
  program_id?: number;
  validation_results?: {
    tools?: { [key: number]: ToolValidation };
    wcs_offset?: WCSValidation | null;
    valid?: boolean;
  };
}

interface Program {
  id: number;
  original_filename: string;
  version_number: number;
  estimated_runtime_seconds?: number;
  program_metadata?: {
    tools?: Array<{ tool_number: number }>;
  };
}

interface CurrentProgramPaneProps {
  machineId: number;
  machineStatus?: string;
  onExpand?: () => void;
}

export const CurrentProgramPane: React.FC<CurrentProgramPaneProps> = ({ machineId, onExpand }) => {
  const [deployment, setDeployment] = useState<Deployment | null>(null);
  const [program, setProgram] = useState<Program | null>(null);
  const [loading, setLoading] = useState(true);
  const [expandedTools, setExpandedTools] = useState<Set<number>>(new Set());
  const [expandedWCS, setExpandedWCS] = useState<boolean>(false);

  useEffect(() => {
    const fetchCurrentDeployment = async () => {
      try {
        setLoading(true);
        // Fetch current deployment
        const response = await fetch(`${API_BASE_URL}/api/programs/machines/${machineId}/deployments?current_only=true`);
        if (response.ok) {
          const data = await response.json();
          if (data && data.length > 0) {
            const deploymentData = data[0];
            setDeployment(deploymentData);
            
            // Fetch program details if we have a program_id
            if (deploymentData.program_id) {
              try {
                const programResponse = await fetch(`${API_BASE_URL}/api/programs/${deploymentData.program_id}`);
                if (programResponse.ok) {
                  const programData = await programResponse.json();
                  setProgram(programData);
                }
              } catch (err) {
                console.error('Error fetching program details:', err);
                setProgram(null);
              }
            } else {
              setProgram(null);
            }
          } else {
            setDeployment(null);
            setProgram(null);
          }
        }
      } catch (error) {
        console.error('Error fetching current deployment:', error);
        setDeployment(null);
        setProgram(null);
      } finally {
        setLoading(false);
      }
    };

    fetchCurrentDeployment();
    // Refresh every 30 seconds
    const interval = setInterval(fetchCurrentDeployment, 30000);
    return () => clearInterval(interval);
  }, [machineId]);

  const formatRuntime = (seconds?: number): string => {
    if (!seconds || seconds === 0) return 'N/A';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
  };

  const extractONumber = (filename: string): string => {
    const match = filename.match(/O(\d{4})/i);
    return match ? match[1] : 'N/A';
  };

  const toggleToolExpanded = (toolNumber: number) => {
    setExpandedTools((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(toolNumber)) {
        newSet.delete(toolNumber);
      } else {
        newSet.add(toolNumber);
      }
      return newSet;
    });
  };

  const renderToolsValidationTable = () => {
    if (!deployment?.validation_results?.tools) {
      return null;
    }

    const toolsArray = Object.values(deployment.validation_results.tools);

    if (toolsArray.length === 0) {
      return null;
    }

    return (
      <div className="validation-section">
        <div className="section-header">TOOLS & VALIDATION</div>
        <table className="validation-table">
          <thead>
            <tr className="validation-table-header">
              <th>ST</th>
              <th>TOOL#</th>
              <th>ACTUAL</th>
              <th>EXPECTED</th>
              <th>DIFF</th>
              <th>TOL</th>
              <th>RESULT</th>
            </tr>
          </thead>
          <tbody>
            {toolsArray.map((tool) => {
              const isExpanded = expandedTools.has(tool.tool_number);

              // Check if validation data is available
              const validationAvailable = tool.available !== undefined && tool.diameter_match !== undefined && tool.length_sufficient !== undefined;

              if (!validationAvailable) {
                // Tool was detected but not validated - show warning
                return (
                  <tr key={tool.tool_number} className="validation-table-row tool-summary-row">
                    <td className="text-warning">⚠</td>
                    <td>T{String(tool.tool_number).padStart(2, '0')}</td>
                    <td colSpan={4}>
                      <span className="text-warning">NOT CHECKED - Validation data unavailable</span>
                    </td>
                    <td className="text-warning">WARN</td>
                  </tr>
                );
              }
              
              // Check if tool is not referenced in NC (required values are 0)
              const notInNC = tool.required_diameter === 0 && tool.required_length === 0;
              
              if (notInNC) {
                // Tool is available on machine but not referenced in NC program
                return (
                  <tr key={tool.tool_number} className="validation-table-row tool-summary-row">
                    <td className="text-muted">─</td>
                    <td>T{String(tool.tool_number).padStart(2, '0')}</td>
                    <td>
                      Ø{(tool.machine_tool_data.diameter || 0).toFixed(3)}" L{(tool.machine_tool_data.length || 0).toFixed(2)}"
                      {tool.machine_tool_data.tool_name && (
                        <span className="text-muted"> ({tool.machine_tool_data.tool_name})</span>
                      )}
                    </td>
                    <td className="text-muted">────</td>
                    <td className="text-muted">────</td>
                    <td className="text-muted">─</td>
                    <td className="text-muted">N/A</td>
                  </tr>
                );
              }

              // Determine overall status
              const toolPassed = tool.available && tool.diameter_match && tool.length_sufficient;
              const hasError = !tool.available || !tool.length_sufficient;
              const hasWarning = tool.available && !tool.diameter_match;
              const statusClass = hasError ? 'text-error' : hasWarning ? 'text-warning' : 'text-success';
              const statusIcon = hasError ? '✕' : hasWarning ? '⚠' : '✓';
              const expandIcon = isExpanded ? '▼' : '▶';

              // Calculate values for length and diameter
              const actualLength = tool.machine_tool_data.length || 0;
              const requiredLength = tool.required_length;
              const lengthDiff = actualLength - requiredLength;
              const lengthPassed = tool.length_sufficient;

              const actualDiameter = tool.machine_tool_data.diameter || 0;
              const requiredDiameter = tool.required_diameter;
              const diameterDiff = actualDiameter - requiredDiameter;
              const diameterPassed = tool.diameter_match;

              return (
                <React.Fragment key={tool.tool_number}>
                  {/* Summary Row */}
                  <tr
                    className="validation-table-row tool-summary-row"
                    onClick={() => tool.available && toggleToolExpanded(tool.tool_number)}
                    style={{ cursor: tool.available ? 'pointer' : 'default' }}
                  >
                    <td className={statusClass}>{statusIcon}</td>
                    <td>
                      {tool.available && <span className="expand-icon">{expandIcon}</span>}
                      T{String(tool.tool_number).padStart(2, '0')}
                    </td>
                    <td colSpan={4}>
                      {!tool.available ? (
                        <span className="text-error">NOT AVAILABLE</span>
                      ) : (
                        <>
                          {tool.machine_tool_data.tool_name && (
                            <span className="text-muted">{tool.machine_tool_data.tool_name}</span>
                          )}
                        </>
                      )}
                    </td>
                    <td className={statusClass}>
                      {toolPassed ? 'PASS' : 'FAIL'}
                    </td>
                  </tr>

                  {/* Detail Rows - Length */}
                  {isExpanded && tool.available && (
                    <tr className="validation-table-row tool-detail-row">
                      <td></td>
                      <td className="detail-label">Length</td>
                      <td>{actualLength.toFixed(2)}"</td>
                      <td>{requiredLength.toFixed(2)}"</td>
                      <td className={lengthPassed ? 'text-success' : 'text-error'}>
                        {lengthDiff.toFixed(2)}"
                      </td>
                      <td>
                        {tool.length_tolerance_plus !== undefined && tool.length_tolerance_minus !== undefined
                          ? `+${tool.length_tolerance_plus.toFixed(4)}"/-${tool.length_tolerance_minus.toFixed(4)}"`
                          : '-'}
                      </td>
                      <td className={lengthPassed ? 'text-success' : 'text-error'}>
                        {lengthPassed ? '✓' : '✕'}
                      </td>
                    </tr>
                  )}

                  {/* Detail Rows - Diameter */}
                  {isExpanded && tool.available && (
                    <tr className="validation-table-row tool-detail-row">
                      <td></td>
                      <td className="detail-label">Diameter</td>
                      <td>{actualDiameter.toFixed(3)}"</td>
                      <td>{requiredDiameter.toFixed(3)}"</td>
                      <td className={diameterPassed ? 'text-success' : 'text-error'}>
                        {diameterDiff.toFixed(3)}"
                      </td>
                      <td>
                        {tool.diameter_tolerance !== undefined
                          ? `±${tool.diameter_tolerance.toFixed(4)}"`
                          : '-'}
                      </td>
                      <td className={diameterPassed ? 'text-success' : 'text-error'}>
                        {diameterPassed ? '✓' : '✕'}
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    );
  };

  const renderWCSSection = () => {
    const wcsData = deployment?.validation_results?.wcs_offset;

    // Always show WCS section, even if data wasn't included
    if (!wcsData) {
      return (
        <div className="validation-section">
          <div className="section-header">WCS OFFSET</div>
          <table className="validation-table">
            <thead>
              <tr className="validation-table-header">
                <th>ST</th>
                <th>OFFSET</th>
                <th>ACTUAL</th>
                <th>EXPECTED</th>
                <th>DIFF</th>
                <th>TOL</th>
                <th>RESULT</th>
              </tr>
            </thead>
            <tbody>
              <tr className="validation-table-row wcs-summary-row">
                <td className="text-muted">─</td>
                <td>N/A</td>
                <td colSpan={4} className="text-muted">
                  NO WCS DATA AVAILABLE
                </td>
                <td className="text-muted">N/A</td>
              </tr>
            </tbody>
          </table>
        </div>
      );
    }

    // Check if WCS was not specified in NC (expected values are all 0)
    const notInNC = wcsData.expected.x === 0 && 
                    wcsData.expected.y === 0 && 
                    wcsData.expected.z === 0 &&
                    wcsData.warnings?.some(w => w.includes("not specified in NC"));

    if (notInNC) {
      // WCS not specified in NC - show collapsed summary with machine data
      const expandIcon = expandedWCS ? '▼' : '▶';
      
      return (
        <div className="validation-section">
          <div className="section-header">WCS OFFSET</div>
          <table className="validation-table">
            <thead>
              <tr className="validation-table-header">
                <th>ST</th>
                <th>OFFSET</th>
                <th>ACTUAL</th>
                <th>EXPECTED</th>
                <th>DIFF</th>
                <th>TOL</th>
                <th>RESULT</th>
              </tr>
            </thead>
            <tbody>
              <tr 
                className="validation-table-row wcs-summary-row"
                onClick={() => setExpandedWCS(!expandedWCS)}
                style={{ cursor: 'pointer' }}
              >
                <td className="text-warning">⚠</td>
                <td>
                  <span className="expand-icon">{expandIcon}</span>
                  G{wcsData.work_offset}
                </td>
                <td colSpan={4} className="text-muted">
                  XYZ NOT PARSED
                </td>
                <td className="text-warning">WARN</td>
              </tr>

              {expandedWCS && wcsData && ['x', 'y', 'z'].map((axis) => {
                const actual = wcsData.actual[axis as keyof typeof wcsData.actual];
                return (
                  <tr key={axis} className="validation-table-row wcs-detail-row">
                    <td></td>
                    <td className="detail-label">{axis.toUpperCase()}</td>
                    <td>{actual.toFixed(4)}"</td>
                    <td className="text-muted">────</td>
                    <td className="text-muted">────</td>
                    <td className="text-muted">─</td>
                    <td className="text-muted">N/A</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      );
    }

    // Check if validation data is available
    const validationAvailable = wcsData.within_tolerance !== undefined &&
                                 wcsData.actual !== undefined &&
                                 wcsData.expected !== undefined;

    if (!validationAvailable) {
      // WCS was detected but not validated - show warning
      return (
        <div className="validation-section">
          <div className="section-header">WCS OFFSET</div>
          <table className="validation-table">
            <thead>
              <tr className="validation-table-header">
                <th>ST</th>
                <th>OFFSET</th>
                <th>ACTUAL</th>
                <th>EXPECTED</th>
                <th>DIFF</th>
                <th>TOL</th>
                <th>RESULT</th>
              </tr>
            </thead>
            <tbody>
              <tr className="validation-table-row wcs-summary-row">
                <td className="text-warning">⚠</td>
                <td>G{wcsData.work_offset}</td>
                <td colSpan={4}>
                  <span className="text-warning">NOT CHECKED - Validation data unavailable</span>
                </td>
                <td className="text-warning">WARN</td>
              </tr>
            </tbody>
          </table>
        </div>
      );
    }

    const tolerance = wcsData.tolerance;
    const withinTolerance = wcsData.within_tolerance;
    const statusClass = withinTolerance ? 'text-success' : 'text-error';
    const statusIcon = withinTolerance ? '✓' : '✕';
    const expandIcon = expandedWCS ? '▼' : '▶';

    return (
      <div className="validation-section">
        <div className="section-header">WCS OFFSET</div>
        <table className="validation-table">
          <thead>
            <tr className="validation-table-header">
              <th>ST</th>
              <th>OFFSET</th>
              <th>ACTUAL</th>
              <th>EXPECTED</th>
              <th>DIFF</th>
              <th>TOL</th>
              <th>RESULT</th>
            </tr>
          </thead>
          <tbody>
            {/* Summary Row */}
            <tr
              className="validation-table-row wcs-summary-row"
              onClick={() => setExpandedWCS(!expandedWCS)}
              style={{ cursor: 'pointer' }}
            >
              <td className={statusClass}>{statusIcon}</td>
              <td>
                <span className="expand-icon">{expandIcon}</span>
                G{wcsData.work_offset}
              </td>
              <td colSpan={4}>
                <span className="text-muted">X/Y/Z Coordinates</span>
              </td>
              <td className={statusClass}>
                {withinTolerance ? 'PASS' : 'FAIL'}
              </td>
            </tr>

            {/* Detail Rows - X/Y/Z Axes */}
            {expandedWCS && ['x', 'y', 'z'].map((axis) => {
              const actual = wcsData.actual[axis as keyof typeof wcsData.actual];
              const expected = wcsData.expected[axis as keyof typeof wcsData.expected];
              const diff = wcsData.difference[axis as keyof typeof wcsData.difference];
              const absDiff = Math.abs(diff);
              const axisWithinTol = absDiff <= tolerance;
              const axisStatusClass = axisWithinTol ? 'text-success' : 'text-error';
              const axisStatusIcon = axisWithinTol ? '✓' : '✕';

              return (
                <tr key={axis} className="validation-table-row wcs-detail-row">
                  <td></td>
                  <td className="detail-label">{axis.toUpperCase()}</td>
                  <td>{actual.toFixed(4)}"</td>
                  <td>{expected.toFixed(4)}"</td>
                  <td className={axisStatusClass}>{diff.toFixed(4)}"</td>
                  <td>±{tolerance.toFixed(4)}"</td>
                  <td className={axisStatusClass}>{axisStatusIcon}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    );
  };

  return (
    <div 
      className="current-program-pane terminal-box"
      onClick={(e) => e.stopPropagation()}
    >
      <div className="terminal-box-header">
        <div className="terminal-box-top">
          <div className="terminal-box-title-row">
            <span>┌─ CURRENT PROGRAM {'─'.repeat(25)}</span>
            {onExpand && (
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
          <div className="program-loading">LOADING...</div>
        ) : !deployment ? (
          <div className="program-empty">NO PROGRAM DEPLOYED</div>
        ) : (
          <>
            <div className="program-info">
              <div className="program-row">
                <span className="program-label">O-NUMBER:</span>
                <span className="program-value text-info">{extractONumber(deployment.deployed_filename)}</span>
              </div>
              <div className="program-row">
                <span className="program-label">FILENAME:</span>
                <span className="program-value">{deployment.deployed_filename}</span>
              </div>
              {program && (
                <>
                  <div className="program-row">
                    <span className="program-label">ORIGINAL:</span>
                    <span className="program-value">{program.original_filename}</span>
                  </div>
                  {program.version_number > 1 && (
                    <div className="program-row">
                      <span className="program-label">VERSION:</span>
                      <span className="program-value">v{program.version_number}</span>
                    </div>
                  )}
                  {program.estimated_runtime_seconds && (
                    <div className="program-row">
                      <span className="program-label">RUNTIME:</span>
                      <span className="program-value">{formatRuntime(program.estimated_runtime_seconds)}</span>
                    </div>
                  )}
                </>
              )}
              <div className="program-row">
                <span className="program-label">DEPLOYED:</span>
                <span className="program-value">
                  {new Date(deployment.deployed_at).toLocaleString()}
                </span>
              </div>
              {deployment.validation_passed !== undefined && (
                <div className="program-row">
                  <span className="program-label">VALIDATION:</span>
                  <span className={`program-value ${deployment.validation_passed !== false ? 'text-success' : 'text-error'}`}>
                    {deployment.validation_passed !== false ? 'PASSED ✓' : 'FAILED ✕'}
                  </span>
                </div>
              )}
            </div>
            {renderToolsValidationTable()}
            {renderWCSSection()}
          </>
        )}
      </div>
      <div className="terminal-box-footer">
        └{'─'.repeat(42)}┘
      </div>
    </div>
  );
};

