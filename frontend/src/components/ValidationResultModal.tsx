import React from 'react';
import { Modal } from './ui/Modal';
import './ValidationResultModal.css';

interface ToolValidation {
  tool_number: number;
  required_diameter: number;
  required_corner_radius: number;
  required_length: number;
  available: boolean;
  diameter_match: boolean;
  corner_radius_match: boolean;
  length_sufficient: boolean;
  machine_tool_data: {
    tool_name?: string;
    diameter?: number;
    length?: number;
  };
  warnings: string[];
}

interface ValidationResult {
  valid: boolean;
  tools: { [key: number]: ToolValidation };
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

interface ValidationResultModalProps {
  isOpen: boolean;
  onClose: () => void;
  result: ValidationResult | null;
  filename: string;
}

export const ValidationResultModal: React.FC<ValidationResultModalProps> = ({
  isOpen,
  onClose,
  result,
  filename,
}) => {
  if (!result) return null;

  const formatDimension = (value: number) => {
    return value > 0 ? value.toFixed(4) : '────';
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

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={`VALIDATION - ${filename}`}>
      <div className="validation-result">
        {/* Overall Status */}
        <div className={`validation-status ${result.valid ? 'text-success' : 'text-error'}`}>
          {result.valid ? '✓ VALIDATION PASSED' : '✕ VALIDATION FAILED'}
        </div>

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
                    <td className={`validation-result ${getStatusClass(tool)}`}>
                      {tool.available ? (
                        <>
                          {tool.diameter_match ? '✓' : '✕'} DIA {' '}
                          {tool.length_sufficient ? '✓' : '✕'} LEN
                        </>
                      ) : (
                        'MISSING'
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

        {/* Errors */}
        {result.errors.length > 0 && (
          <div className="validation-section">
            <div className="section-header text-error">ERRORS</div>
            {result.errors.map((error, idx) => (
              <div key={idx} className="error-item text-error">
                ✕ {error}
              </div>
            ))}
          </div>
        )}

        {/* Warnings */}
        {result.warnings.length > 0 && (
          <div className="validation-section">
            <div className="section-header text-warning">WARNINGS</div>
            {result.warnings.map((warning, idx) => (
              <div key={idx} className="warning-item text-warning">
                ⚠ {warning}
              </div>
            ))}
          </div>
        )}
      </div>
    </Modal>
  );
};
