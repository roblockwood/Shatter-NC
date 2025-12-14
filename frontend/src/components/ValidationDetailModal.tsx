import React, { useState } from 'react';
import { Modal } from './ui/Modal';
import './ValidationDetailModal.css';

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

interface ValidationResult {
  valid: boolean;
  tools: { [key: number]: ToolValidation };
  wcs_offset: WCSValidation | null;
  warnings: string[];
  errors: string[];
  metadata: {
    posted_date?: string;
    estimated_runtime_seconds?: number;
    tool_count: number;
    line_count: number;
    file_size: number;
  };
}

interface ValidationDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  result: ValidationResult | null;
  filename: string;
  machineName: string;
}

export const ValidationDetailModal: React.FC<ValidationDetailModalProps> = ({
  isOpen,
  onClose,
  result,
  filename,
}) => {
  const [expandedTools, setExpandedTools] = useState<Set<number>>(new Set());
  const [expandedWCS, setExpandedWCS] = useState(false);

  if (!result) return null;

  const toggleToolExpanded = (toolNumber: number) => {
    const newExpanded = new Set(expandedTools);
    if (newExpanded.has(toolNumber)) {
      newExpanded.delete(toolNumber);
    } else {
      newExpanded.add(toolNumber);
    }
    setExpandedTools(newExpanded);
  };

  const formatCoordinate = (value: number) => {
    return value.toFixed(4);
  };

  const formatTolerance = (value: number) => {
    return `±${value.toFixed(4)}`;
  };

  const formatRuntime = (seconds: number | undefined) => {
    if (!seconds) return '──:──:──';
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    return `${String(hrs).padStart(2, '0')}:${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
  };

  const renderFooter = () => {
    return (
      <div className="detail-modal-footer">
        <button
          className="terminal-button cancel"
          onClick={onClose}
        >
          [ CLOSE ]
        </button>
      </div>
    );
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`VALIDATION DETAILS - ${filename}`}
      footer={renderFooter()}
    >
      <div className="validation-detail">
        {/* Overall Status */}
        <div className={`validation-status ${result.valid ? 'text-success' : 'text-error'}`}>
          <div className="status-text">
            {result.valid ? '✓ VALIDATION PASSED' : '✕ VALIDATION FAILED'}
          </div>
        </div>

        {/* Errors Section */}
        {(result.errors.length > 0 || (result.wcs_offset && !result.wcs_offset.within_tolerance)) && (
          <div className="validation-section errors-section">
            <div className="section-header text-error">ERRORS</div>
            {result.errors.filter(error => !error.includes('WCS')).map((error, idx) => (
              <div key={idx} className="error-item text-error">
                ✕ {error}
              </div>
            ))}
            {result.wcs_offset && !result.wcs_offset.within_tolerance && (
              <>
                <div className="error-item text-error">
                  ✕ WCS OFFSET G{result.wcs_offset.work_offset} OUT OF TOLERANCE
                </div>
                {result.wcs_offset.warnings.map((warning, idx) => (
                  <div key={`wcs-${idx}`} className="error-item text-error wcs-error-detail">
                    {warning}
                  </div>
                ))}
              </>
            )}
          </div>
        )}

        {/* Metadata */}
        <div className="validation-section">
          <div className="section-header">PROGRAM INFO</div>
          <div className="metadata-grid">
            <div className="metadata-row">
              <span className="label">LINES:</span>
              <span className="value">{result.metadata.line_count}</span>
            </div>
            <div className="metadata-row">
              <span className="label">SIZE:</span>
              <span className="value">{(result.metadata.file_size / 1024).toFixed(1)} KB</span>
            </div>
            <div className="metadata-row">
              <span className="label">TOOLS:</span>
              <span className="value">{result.metadata.tool_count}</span>
            </div>
            <div className="metadata-row">
              <span className="label">RUNTIME:</span>
              <span className="value">{formatRuntime(result.metadata.estimated_runtime_seconds)}</span>
            </div>
          </div>
        </div>

        {/* Tool Validation Results */}
        <div className="validation-section">
          <div className="section-header">TOOLS</div>
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
              {Object.values(result.tools).map((tool) => {
                const isExpanded = expandedTools.has(tool.tool_number);
                
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
                        <td>-</td>
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
                        <td>-</td>
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

        {/* WCS Offset Validation Results */}
        {result.wcs_offset && (() => {
          // Check if WCS was not specified in NC (expected values are all 0)
          const notInNC = result.wcs_offset.expected.x === 0 && 
                          result.wcs_offset.expected.y === 0 && 
                          result.wcs_offset.expected.z === 0 &&
                          result.wcs_offset.warnings.some(w => w.includes("not specified in NC"));

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
                        G{result.wcs_offset.work_offset}
                      </td>
                      <td colSpan={4} className="text-muted">
                        XYZ NOT PARSED
                      </td>
                      <td className="text-warning">WARN</td>
                    </tr>

                    {expandedWCS && result.wcs_offset && ['x', 'y', 'z'].map((axis) => {
                      const actual = result.wcs_offset!.actual[axis as keyof typeof result.wcs_offset.actual];
                      return (
                        <tr key={axis} className="validation-table-row wcs-detail-row">
                          <td></td>
                          <td className="axis-label">{axis.toUpperCase()}</td>
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

          // WCS found in NC - show validation results
          const tolerance = result.wcs_offset.tolerance;
          const withinTolerance = result.wcs_offset.within_tolerance;
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
                      G{result.wcs_offset.work_offset}
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
                    const expected = result.wcs_offset!.expected[axis as keyof typeof result.wcs_offset.expected];
                    const actual = result.wcs_offset!.actual[axis as keyof typeof result.wcs_offset.actual];
                    const difference = result.wcs_offset!.difference[axis as keyof typeof result.wcs_offset.difference];
                    const withinTol = difference <= tolerance;

                    return (
                      <tr key={axis} className="validation-table-row wcs-detail-row">
                        <td></td>
                        <td className="axis-label">{axis.toUpperCase()}</td>
                        <td>{formatCoordinate(actual)}"</td>
                        <td>{formatCoordinate(expected)}"</td>
                        <td className={withinTol ? 'text-success' : 'text-error'}>
                          {formatCoordinate(difference)}"
                        </td>
                        <td>{formatTolerance(tolerance)}</td>
                        <td className={withinTol ? 'text-success' : 'text-error'}>
                          {withinTol ? '✓' : '✕'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          );
        })()}
      </div>
    </Modal>
  );
};
