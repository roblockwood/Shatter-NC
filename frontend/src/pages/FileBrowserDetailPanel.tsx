import React, { useState, useEffect } from 'react';
import { Select } from '../components/ui';
import type {
  Program,
  DeploymentDetail,
  FreshValidationState,
  ToolValidation,
} from './FileBrowserTypes';
import { formatBytes, formatDate, formatRuntime, isONumberFile } from './FileBrowserUtils';
import { IS_DEMO_MODE } from '../config/demo';

export interface FileBrowserDetailPanelProps {
  selectedProgram: Program;
  deploymentDetail: DeploymentDetail | null;
  deploymentLoading: boolean;
  deploymentError: string | null;
  freshValidation: FreshValidationState | null;
  expandedTools: Set<number>;
  expandedWCS: boolean;
  selectedDeploymentId: number | null;
  validationError: string | null;
  validationLoading: boolean;
  previewLines: string[];
  metadataLoading: boolean;
  deploymentSectionRef: React.RefObject<HTMLDivElement | null>;
  setExpandedWCS: (v: boolean) => void;
  setSelectedDeploymentId: (id: number | null) => void;
  setValidationError: (err: string | null) => void;
  toggleToolExpanded: (toolNumber: number) => void;
  onDownload: (program: Program) => void;
  onValidate: (program: Program) => void;
  onViewCode: (program: Program) => void;
}

export const FileBrowserDetailPanel: React.FC<FileBrowserDetailPanelProps> = ({
  selectedProgram,
  deploymentDetail,
  deploymentLoading,
  deploymentError,
  freshValidation,
  expandedTools,
  expandedWCS,
  selectedDeploymentId,
  validationError,
  validationLoading,
  previewLines,
  metadataLoading,
  deploymentSectionRef,
  setExpandedWCS,
  setSelectedDeploymentId,
  setValidationError,
  toggleToolExpanded,
  onDownload,
  onValidate,
  onViewCode,
}) => {
  const [progressState, setProgressState] = useState(0);
  // eslint-disable-next-line react-hooks/purity
  const now = Date.now();

  useEffect(() => {
    if (!metadataLoading) return;
    const interval = setInterval(() => {
      setProgressState(prev => (prev + 1) % 8);
    }, 150);
    return () => clearInterval(interval);
  }, [metadataLoading]);

  const renderProgressBar = () => {
    const stages = [
      '[████░░░░░]',
      '[██████░░░]',
      '[████████░]',
      '[██████████]',
      '[██████████]',
      '[████████░░]',
      '[██████░░░░]',
      '[████░░░░░░]',
    ];
    return <span className="ascii-progress-container">{stages[progressState]} PARSING...</span>;
  };

  return (
    <div className="details-panel">
      <div className="panel-header">
        ┌─ SELECTED: {selectedProgram.name} {'─'.repeat(30)}┐
      </div>
      <div className="details-content" style={{ overflow: 'auto' }}>
        {/* FILE INFO SECTION */}
        <div className="detail-section">
          <div className="section-title">FILE INFO</div>
          <div className="detail-row">
            <span className="label">SIZE:</span>
            <span className="value">{formatBytes(selectedProgram.size)}</span>
          </div>
          <div className="detail-row">
            <span className="label">MODIFIED:</span>
            <span className="value">{formatDate(selectedProgram.modified)}</span>
          </div>
        </div>

        {/* DEPLOYMENT INFO SECTION (O-number files only) */}
        {isONumberFile(selectedProgram.name) && (
          <div className="detail-section" ref={deploymentSectionRef}>
            <div className="deployment-info-header">
              <div className="section-title">
                {freshValidation ? (
                  <span style={{ color: '#4ade80' }}>*FRESH* VALIDATION RESULTS</span>
                ) : (
                  'DEPLOYMENT INFO'
                )}
              </div>
              {freshValidation && (
                <span className="validation-timestamp text-muted">
                  Validated: {new Date(freshValidation.timestamp).toLocaleTimeString()}
                </span>
              )}
              {!freshValidation && deploymentDetail?.history && deploymentDetail.history.length > 1 && (
                <Select
                  value={selectedDeploymentId?.toString() || ''}
                  onChange={(value) => setSelectedDeploymentId(value ? parseInt(value) : null)}
                  options={[
                    {
                      value: '',
                      label: `${deploymentDetail.program?.original_filename} (${formatDate(deploymentDetail.deployment.deployed_at)}) - CURRENT`
                    },
                    ...deploymentDetail.history.slice(1).map((entry) => ({
                      value: entry.id.toString(),
                      label: `${entry.original_filename} (${formatDate(entry.deployed_at)})`
                    }))
                  ]}
                  className="deployment-selector"
                />
              )}
            </div>

            {validationError && (
              <div className="validation-error">
                <div className="detail-row">
                  <span className="value text-error">X {validationError}</span>
                </div>
                <div className="error-actions">
                  <button
                    className="terminal-button-sm"
                    onClick={() => onValidate(selectedProgram)}
                  >
                    [ RETRY ]
                  </button>
                  <button
                    className="terminal-button-sm"
                    onClick={() => setValidationError(null)}
                  >
                    [ DISMISS ]
                  </button>
                </div>
              </div>
            )}

            {freshValidation ? (
              <>
                <div className="detail-row">
                  <span className="label">STATUS:</span>
                  <span className={`value ${freshValidation.validation.valid ? 'text-success' : 'text-error'}`}>
                    {freshValidation.validation.valid ? '✓ PASSED' : '✕ FAILED'}
                  </span>
                </div>

                {(() => {
                  const age = now - freshValidation.timestamp; // now captured above
                  const STALE_MS = 5 * 60 * 1000;
                  return age > STALE_MS && (
                    <div className="detail-row">
                      <span className="value text-warning">
                        ! Validation is {Math.floor(age / 60000)} minutes old. Machine state may have changed.
                      </span>
                    </div>
                  );
                })()}

                {freshValidation.validation.errors && freshValidation.validation.errors.length > 0 && (
                  <div className="detail-row">
                    <span className="label">ERRORS:</span>
                    <div className="value text-error">
                      {freshValidation.validation.errors.map((err, i) => (
                        <div key={i}>- {err}</div>
                      ))}
                    </div>
                  </div>
                )}

                {freshValidation.validation.warnings && freshValidation.validation.warnings.length > 0 && (
                  <div className="detail-row">
                    <span className="label">WARNINGS:</span>
                    <div className="value text-warning">
                      {freshValidation.validation.warnings.map((warn, i) => (
                        <div key={i}>- {warn}</div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            ) : (
              <>
                {deploymentLoading && (
                  <div className="detail-row">
                    <span className="value">{renderProgressBar()}</span>
                  </div>
                )}
                {deploymentError && (
                  <div className="detail-row">
                    <span className="value text-error">{deploymentError}</span>
                  </div>
                )}
                {deploymentDetail && (
                  <>
                    <div className="detail-row">
                      <span className="label">DEPLOYED:</span>
                      <span className="value">
                        {formatDate(deploymentDetail.deployment.deployed_at)}
                      </span>
                    </div>
                    <div className="detail-row">
                      <span className="label">POSTED DATE:</span>
                      <span className="value">
                        {deploymentDetail.program?.posted_date ? formatDate(deploymentDetail.program.posted_date) : 'N/A'}
                      </span>
                    </div>
                    <div className="detail-row">
                      <span className="label">RUNTIME:</span>
                      <span className="value">
                        {formatRuntime(deploymentDetail.program?.estimated_runtime_seconds || 0)}
                      </span>
                    </div>
                    <div className="detail-row">
                      <span className="label">VALIDATION:</span>
                      <span className={`value ${
                        deploymentDetail.deployment.validation_passed === null ? 'text-muted' :
                        deploymentDetail.deployment.validation_passed ? 'text-success' : 'text-error'
                      }`}>
                        {deploymentDetail.deployment.validation_passed === null ? '─ not validated ─' :
                         deploymentDetail.deployment.validation_passed ? '✓ PASSED' : '✕ FAILED'}
                      </span>
                    </div>
                  </>
                )}
              </>
            )}
          </div>
        )}

        {/* TOOL DETAILS TABLE (O-number files with deployment) */}
        {((deploymentDetail?.deployment?.validation_results?.tools && !freshValidation) ||
          (freshValidation?.validation?.tools)) && (
          <div className="detail-section">
            <div className="section-title">TOOLS</div>
            <div className="tools-table">
              <table className="detail-table">
                <thead>
                  <tr>
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
                  {Object.entries((freshValidation?.validation?.tools || deploymentDetail?.deployment?.validation_results?.tools || {})).map(([toolKey, validation]: [string, ToolValidation]) => {
                    const toolNumber = parseInt(toolKey, 10);
                    if (isNaN(toolNumber)) return null;
                    const isExpanded = expandedTools.has(toolNumber);

                    const notInNC = validation.required_diameter === 0 && validation.required_length === 0;
                    if (notInNC) {
                      return (
                        <tr key={toolNumber} className="tool-summary-row">
                          <td className="text-muted">─</td>
                          <td>T{String(toolNumber).padStart(2, '0')}</td>
                          <td>
                            Ø{(validation.machine_tool_data?.diameter || 0).toFixed(3)}" L{(validation.machine_tool_data?.length || 0).toFixed(2)}"
                            {validation.machine_tool_data?.tool_name && (
                              <span className="text-muted"> ({validation.machine_tool_data.tool_name})</span>
                            )}
                          </td>
                          <td className="text-muted">────</td>
                          <td className="text-muted">────</td>
                          <td className="text-muted">─</td>
                          <td className="text-muted">N/A</td>
                        </tr>
                      );
                    }

                    const toolPassed = validation.available && validation.diameter_match && validation.length_sufficient;
                    const hasError = !validation.available || !validation.length_sufficient;
                    const hasWarning = validation.available && !validation.diameter_match;
                    const statusClass = hasError ? 'text-error' : hasWarning ? 'text-warning' : 'text-success';
                    const statusIcon = hasError ? '✕' : hasWarning ? '⚠' : '✓';
                    const expandIcon = isExpanded ? '▼' : '▶';

                    const actualLength = validation.machine_tool_data?.length || 0;
                    const requiredLength = validation.required_length || 0;
                    const lengthDiff = actualLength - requiredLength;

                    const actualDiameter = validation.machine_tool_data?.diameter || 0;
                    const requiredDiameter = validation.required_diameter || 0;
                    const diameterDiff = actualDiameter - requiredDiameter;

                    return (
                      <React.Fragment key={toolNumber}>
                        {/* Summary Row */}
                        <tr
                          className="tool-summary-row clickable"
                          onClick={() => validation.available && toggleToolExpanded(toolNumber)}
                          style={{ cursor: validation.available ? 'pointer' : 'default' }}
                        >
                          <td className={statusClass}>{statusIcon}</td>
                          <td>
                            {validation.available && <span className="expand-icon">{expandIcon}</span>}
                            T{String(toolNumber).padStart(2, '0')}
                          </td>
                          <td colSpan={4}>
                            {!validation.available ? (
                              <span className="text-error">NOT AVAILABLE</span>
                            ) : (
                              <>
                                {validation.machine_tool_data?.tool_name && (
                                  <span className="text-muted">{validation.machine_tool_data.tool_name}</span>
                                )}
                              </>
                            )}
                          </td>
                          <td className={statusClass}>
                            {toolPassed ? 'PASS' : 'FAIL'}
                          </td>
                        </tr>

                        {/* Detail Rows - Length */}
                        {isExpanded && validation.available && (
                          <tr className="tool-detail-row">
                            <td></td>
                            <td className="detail-label">Length</td>
                            <td>{actualLength.toFixed(2)}"</td>
                            <td>{requiredLength.toFixed(2)}"</td>
                            <td className={validation.length_sufficient ? 'text-success' : 'text-error'}>
                              {lengthDiff.toFixed(2)}"
                            </td>
                            <td>
                              {validation.length_tolerance_plus !== undefined && validation.length_tolerance_minus !== undefined
                                ? `+${validation.length_tolerance_plus.toFixed(4)}"/-${validation.length_tolerance_minus.toFixed(4)}"`
                                : '-'}
                            </td>
                            <td className={validation.length_sufficient ? 'text-success' : 'text-error'}>
                              {validation.length_sufficient ? '✓' : '✕'}
                            </td>
                          </tr>
                        )}

                        {/* Detail Rows - Diameter */}
                        {isExpanded && validation.available && (
                          <tr className="tool-detail-row">
                            <td></td>
                            <td className="detail-label">Diameter</td>
                            <td>{actualDiameter.toFixed(3)}"</td>
                            <td>{requiredDiameter.toFixed(3)}"</td>
                            <td className={validation.diameter_match ? 'text-success' : 'text-error'}>
                              {diameterDiff.toFixed(3)}"
                            </td>
                            <td>
                              {validation.diameter_tolerance !== undefined
                                ? `±${validation.diameter_tolerance.toFixed(4)}"`
                                : '-'}
                            </td>
                            <td className={validation.diameter_match ? 'text-success' : 'text-error'}>
                              {validation.diameter_match ? '✓' : '✕'}
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* WCS VALIDATION TABLE */}
        {((deploymentDetail?.deployment?.validation_results?.wcs_offset && !freshValidation) ||
          (freshValidation?.validation?.wcs_offset)) && (() => {
          const wcs = freshValidation?.validation?.wcs_offset || deploymentDetail?.deployment?.validation_results?.wcs_offset;
          if (!wcs) return null;

          const notInNC = wcs.expected.x === 0 &&
                          wcs.expected.y === 0 &&
                          wcs.expected.z === 0 &&
                          wcs.warnings?.some((w: string) => w.includes("not specified in NC"));

          if (notInNC) {
            const expandIcon = expandedWCS ? '▼' : '▶';
            return (
              <div className="detail-section">
                <div className="section-title">WCS OFFSET</div>
                <div className="wcs-validation">
                  <table className="detail-table">
                    <thead>
                      <tr>
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
                        className="wcs-summary-row clickable"
                        onClick={() => setExpandedWCS(!expandedWCS)}
                        style={{ cursor: 'pointer' }}
                      >
                        <td className="text-warning">⚠</td>
                        <td>
                          <span className="expand-icon">{expandIcon}</span>
                          G{wcs.work_offset}
                        </td>
                        <td colSpan={4} className="text-muted">
                          XYZ NOT PARSED
                        </td>
                        <td className="text-warning">WARN</td>
                      </tr>

                      {expandedWCS && ['x', 'y', 'z'].map((axis) => {
                        const actual = (wcs.actual as Record<string, number>)[axis];
                        return (
                          <tr key={axis} className="wcs-detail-row">
                            <td></td>
                            <td className="detail-label">{axis.toUpperCase()}</td>
                            <td>{(actual || 0).toFixed(4)}"</td>
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
              </div>
            );
          }

          const withinTolerance = wcs.within_tolerance;
          const statusClass = withinTolerance ? 'text-success' : 'text-error';
          const statusIcon = withinTolerance ? '✓' : '✕';
          const expandIcon = expandedWCS ? '▼' : '▶';

          return (
            <div className="detail-section">
              <div className="section-title">WCS OFFSET</div>
              <div className="wcs-validation">
                <table className="detail-table">
                  <thead>
                    <tr>
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
                      className="wcs-summary-row clickable"
                      onClick={() => setExpandedWCS(!expandedWCS)}
                      style={{ cursor: 'pointer' }}
                    >
                      <td className={statusClass}>{statusIcon}</td>
                      <td>
                        <span className="expand-icon">{expandIcon}</span>
                        G{wcs.work_offset}
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
                      const expected = (wcs.expected as Record<string, number>)[axis];
                      const actual = (wcs.actual as Record<string, number>)[axis];
                      const difference = (wcs.difference as Record<string, number>)[axis];
                      const diff = Math.abs(difference || 0);
                      const withinTol = diff <= (wcs.tolerance || 0.1);

                      return (
                        <tr key={axis} className="wcs-detail-row">
                          <td></td>
                          <td className="detail-label">{axis.toUpperCase()}</td>
                          <td>{(actual || 0).toFixed(4)}"</td>
                          <td>{(expected || 0).toFixed(4)}"</td>
                          <td className={withinTol ? 'text-success' : 'text-error'}>
                            {diff.toFixed(4)}"
                          </td>
                          <td>±{(wcs.tolerance || 0.1).toFixed(4)}</td>
                          <td className={withinTol ? 'text-success' : 'text-error'}>
                            {withinTol ? '✓' : '✕'}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          );
        })()}

        {/* ACTIONS SECTION */}
        <div className="detail-actions">
          <button
            className="terminal-button"
            onClick={() => onDownload(selectedProgram)}
          >
            [ DOWNLOAD ]
          </button>
          {selectedProgram.name.toUpperCase().endsWith('.NC') && (
            <button
              className="terminal-button"
              onClick={() => onViewCode(selectedProgram)}
            >
              [ VIEW CODE ]
            </button>
          )}
          {selectedProgram.name.match(/^O\d{4}\.NC$/i) && !IS_DEMO_MODE && (
            validationLoading ? (
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span>{renderProgressBar()}</span>
                <span className="text-muted">Downloading and validating...</span>
              </div>
            ) : (
              <button
                className="terminal-button"
                onClick={() => onValidate(selectedProgram)}
              >
                [ VALIDATE ]
              </button>
            )
          )}
        </div>

        {/* CODE PREVIEW SECTION */}
        {previewLines.length > 0 && selectedProgram.name.toUpperCase().endsWith('.NC') && (
          <div className="code-preview">
            <div className="preview-header">┌─ PREVIEW (First 50 Lines) ─────────────┐</div>
            <div className="preview-content">
              {previewLines.map((line, idx) => (
                <div key={idx} className="preview-line">
                  <span className="line-number">{idx + 1}</span>
                  <span className="line-text">{line || ' '}</span>
                </div>
              ))}
            </div>
            <div className="preview-footer">└─────────────────────────────────────┘</div>
          </div>
        )}
      </div>
      <div className="panel-footer">
        └{'─'.repeat(50)}┘
      </div>
    </div>
  );
};
