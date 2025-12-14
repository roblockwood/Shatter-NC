import React from 'react';
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
  if (!result) return null;

  const formatDimension = (value: number) => {
    return value > 0 ? value.toFixed(4) : '────';
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

  const getStatusIcon = (tool: ToolValidation) => {
    if (!tool.available) return '✕';
    if (!tool.diameter_match || !tool.length_sufficient) return '⚠';
    return '✓';
  };

  const getStatusClass = (tool: ToolValidation) => {
    if (!tool.available) return 'text-error';
    if (!tool.diameter_match || !tool.length_sufficient) return 'text-warning';
    return 'text-success';
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
          <div className="section-header">TOOL VALIDATION</div>
          <table className="validation-table">
            <thead>
              <tr className="validation-table-header">
                <th>ST</th>
                <th>T#</th>
                <th>REQUIRED</th>
                <th>AVAILABLE</th>
                <th>STATUS</th>
              </tr>
              <tr className="validation-table-divider">
                <td colSpan={5}>├{'─'.repeat(80)}┤</td>
              </tr>
            </thead>
            <tbody>
              {Object.values(result.tools).map((tool) => (
                <React.Fragment key={tool.tool_number}>
                  <tr className="validation-table-row">
                    <td className={`validation-status-icon ${getStatusClass(tool)}`}>
                      {getStatusIcon(tool)}
                    </td>
                    <td className="tool-number">
                      T{String(tool.tool_number).padStart(2, '0')}
                    </td>
                    <td className="tool-specs">
                      Ø{formatDimension(tool.required_diameter)}" L{formatDimension(tool.required_length)}"
                    </td>
                    <td className="tool-specs">
                      {tool.available ? (
                        <>
                          Ø{formatDimension(tool.machine_tool_data.diameter || 0)}" L{formatDimension(tool.machine_tool_data.length || 0)}"
                          {tool.machine_tool_data.tool_name && (
                            <span className="text-muted"> ({tool.machine_tool_data.tool_name})</span>
                          )}
                        </>
                      ) : (
                        <span className="text-error">NOT LOADED</span>
                      )}
                    </td>
                    <td className="validation-result">
                      {tool.available ? (
                        <>
                          <span className={tool.diameter_match ? 'text-success' : 'text-error'}>
                            {tool.diameter_match ? '✓' : '✕'} DIA
                          </span>
                          {' '}
                          <span className={tool.length_sufficient ? 'text-success' : 'text-error'}>
                            {tool.length_sufficient ? '✓' : '✕'} LEN
                          </span>
                        </>
                      ) : (
                        <span className="text-error">MISSING</span>
                      )}
                    </td>
                  </tr>
                  {tool.warnings.length > 0 && (
                    <tr className="validation-warning-row">
                      <td></td>
                      <td colSpan={4} className="text-warning">
                        {tool.warnings.map((w, idx) => (
                          <div key={idx}>⚠ {w}</div>
                        ))}
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>

        {/* WCS Offset Validation Results */}
        {result.wcs_offset && (
          <div className="validation-section">
            <div className="section-header text-success">
              WCS OFFSET VALIDATION (G{result.wcs_offset.work_offset})
            </div>
            <table className="validation-table">
              <thead>
                <tr className="validation-table-header">
                  <th>AXIS</th>
                  <th>EXPECTED</th>
                  <th>ACTUAL</th>
                  <th>DIFF</th>
                  <th>TOLERANCE</th>
                  <th>STATUS</th>
                </tr>
                <tr className="validation-table-divider">
                  <td colSpan={6}>├{'─'.repeat(80)}┤</td>
                </tr>
              </thead>
              <tbody>
                {['x', 'y', 'z'].map((axis) => {
                  const axisUpper = axis.toUpperCase();
                  const expected = result.wcs_offset!.expected[axis as keyof typeof result.wcs_offset.expected];
                  const actual = result.wcs_offset!.actual[axis as keyof typeof result.wcs_offset.actual];
                  const difference = result.wcs_offset!.difference[axis as keyof typeof result.wcs_offset.difference];
                  const tolerance = result.wcs_offset!.tolerance;
                  const withinTol = difference <= tolerance;

                  return (
                    <tr key={axis} className="validation-table-row">
                      <td className="axis-label">{axisUpper}</td>
                      <td className="coordinate-value">{formatCoordinate(expected)}"</td>
                      <td className="coordinate-value">{formatCoordinate(actual)}"</td>
                      <td className={`coordinate-value ${withinTol ? 'text-success' : 'text-error'}`}>
                        {formatCoordinate(difference)}"
                      </td>
                      <td className="coordinate-value">{formatTolerance(tolerance)}</td>
                      <td className={`validation-result ${withinTol ? 'text-success' : 'text-error'}`}>
                        {withinTol ? '✓ OK' : '✕ OUT'}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </Modal>
  );
};
