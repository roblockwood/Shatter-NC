import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Modal } from './ui/Modal';
import './UploadConfirmationModal.css';
import { API_BASE_URL } from '../config/api';

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

interface UploadConfirmationModalProps {
  isOpen: boolean;
  onClose: () => void;
  result: ValidationResult | null;
  filename: string;
  machineId: number;
  machineName: string;
  machinePath: string;
  fileContent: string;
}

export const UploadConfirmationModal: React.FC<UploadConfirmationModalProps> = ({
  isOpen,
  onClose,
  result,
  filename,
  machineId,
  machineName,
  machinePath,
  fileContent,
}) => {
  const navigate = useNavigate();
  const [customONumber, setCustomONumber] = useState('O2000.nc');
  const [isReplacingExisting, setIsReplacingExisting] = useState(false);
  const [replacementInfo, setReplacementInfo] = useState<any>(null);
  const [isLoadingONumber, setIsLoadingONumber] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [deployedInfo, setDeployedInfo] = useState<any>(null);
  const [closeCountdown, setCloseCountdown] = useState(0);
  const onCloseRef = useRef(onClose);
  const [expandedTools, setExpandedTools] = useState<Set<number>>(new Set());
  const [expandedWCS, setExpandedWCS] = useState(false);

  // Update ref when onClose changes
  useEffect(() => {
    onCloseRef.current = onClose;
  }, [onClose]);

  // Fetch next O-number when modal opens
  useEffect(() => {
    if (isOpen && machineId && result) {
      fetchNextONumber();
    }
  }, [isOpen, machineId, result]);

  // Auto-close success screen after 5 seconds with countdown
  useEffect(() => {
    if (uploadSuccess && closeCountdown > 0) {
      const countdownInterval = setInterval(() => {
        setCloseCountdown((prev) => {
          if (prev <= 1) {
            clearInterval(countdownInterval);
            // Reset upload state before closing
            setUploadSuccess(false);
            setUploadProgress(0);
            setUploadError(null);
            setIsUploading(false);
            setCustomONumber('O2000.nc');
            setDeployedInfo(null);
            setCloseCountdown(0);
            // Then call parent close
            onCloseRef.current();
            return 0;
          }
          return prev - 1;
        });
      }, 1000);

      return () => clearInterval(countdownInterval);
    }
  }, [uploadSuccess, closeCountdown]);

  // Reset all upload state when modal closes
  useEffect(() => {
    if (!isOpen) {
      setUploadSuccess(false);
      setUploadProgress(0);
      setUploadError(null);
      setIsUploading(false);
      setCustomONumber('O2000.nc');
      setDeployedInfo(null);
      setCloseCountdown(0);
      setExpandedTools(new Set());
      setExpandedWCS(false);
    }
  }, [isOpen]);

  if (!result) return null;

  const fetchNextONumber = async () => {
    if (!machineId) return;

    setIsLoadingONumber(true);
    try {
      const url = new URL(`${API_BASE_URL}/api/programs/machines/${machineId}/next-onumber`);
      if (filename) {
        url.searchParams.append('filename', filename);
      }
      const response = await fetch(url.toString());
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const data = await response.json();

      setCustomONumber(data.next_onumber);
      setIsReplacingExisting(data.is_replacing);
      setReplacementInfo(data.replacement_info);
    } catch (error) {
      console.error('Error fetching O-number:', error);
      setCustomONumber('O2000.nc');
    } finally {
      setIsLoadingONumber(false);
    }
  };

  const performUpload = async () => {
    if (!machineId || !fileContent || !customONumber || !machinePath) {
      setUploadError('Missing required parameters');
      return;
    }

    setIsUploading(true);
    setUploadError(null);
    setUploadProgress(0);

    try {
      // Step 1: Upload via FTP
      const uploadPath = `${machinePath}/${customONumber}`;
      const uploadUrl = `${API_BASE_URL}/api/machines/${machineId}/upload?file_path=${encodeURIComponent(uploadPath)}`;

      const blob = new Blob([fileContent], { type: 'text/plain' });
      const formData = new FormData();
      formData.append('file', blob, customONumber);

      await new Promise<void>((resolve, reject) => {
        const xhr = new XMLHttpRequest();

        xhr.upload.addEventListener('progress', (e) => {
          if (e.lengthComputable) {
            setUploadProgress(Math.round((e.loaded / e.total) * 100));
          }
        });

        xhr.addEventListener('load', () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            resolve();
          } else {
            reject(new Error(`HTTP ${xhr.status}`));
          }
        });

        xhr.addEventListener('error', () => reject(new Error('Network error')));
        xhr.open('POST', uploadUrl);
        xhr.send(formData);
      });

      // Step 2: Store in database with validation results
      const dbResponse = await fetch(`${API_BASE_URL}/api/programs/upload`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          gcode_content: fileContent,
          original_filename: filename,
          machine_id: machineId,
          deployed_filename: customONumber,
          validate_before_upload: false,
          validation_results: result
        })
      });

      if (!dbResponse.ok) {
        throw new Error('Failed to save to database');
      }

      // Success
      setUploadSuccess(true);
      setDeployedInfo({
        onumber: customONumber,
        path: uploadPath,
        machine: machineName,
        was_replacement: isReplacingExisting,
        replacement_details: replacementInfo
      });
      setUploadProgress(100);
      setCloseCountdown(5); // Start 5-second countdown

      // Pre-fetch programs list and cache for instant navigation
      fetch(`${API_BASE_URL}/api/machines/${machineId}/programs?path=${encodeURIComponent(machinePath)}`)
        .then(res => res.json())
        .then(data => {
          // Cache the data for instant FileBrowser loading
          const cacheKey = `programs_cache_${machineId}_${machinePath}`;
          const cacheData = {
            programs: data.programs || [],
            timestamp: Date.now(),
            machineId,
            path: machinePath
          };
          sessionStorage.setItem(cacheKey, JSON.stringify(cacheData));
        })
        .catch(() => {
          // Pre-fetch failed, non-critical - FileBrowser will fetch normally
        });

    } catch (error) {
      console.error('Upload error:', error);
      setUploadError(error instanceof Error ? error.message : 'Upload failed');
    } finally {
      setIsUploading(false);
    }
  };

  const handleGoToFileManager = () => {
    // Navigate to FileBrowser with query params
    const navUrl = `/files?machine=${machineId}&file=${customONumber}`;
    navigate(navUrl);

    // Close modal
    onClose();
  };

  const handleClose = () => {
    // Optionally: Call API to explicitly close FTP connection
    fetch(`${API_BASE_URL}/api/machines/${machineId}/close-ftp`, {
      method: 'POST'
    }).catch(() => {/* Ignore errors */});

    onClose();
  };

  const toggleToolExpanded = (toolNumber: number) => {
    setExpandedTools(prev => {
      const newSet = new Set(prev);
      if (newSet.has(toolNumber)) {
        newSet.delete(toolNumber);
      } else {
        newSet.add(toolNumber);
      }
      return newSet;
    });
  };

  const renderToolsSection = () => {
    const toolsArray = Object.values(result.tools);

    return (
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
    );
  };

  const renderWCSSection = () => {
    if (!result.wcs_offset) return null;

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

    // Check if validation data is available
    const validationAvailable = result.wcs_offset.within_tolerance !== undefined &&
                                 result.wcs_offset.actual !== undefined &&
                                 result.wcs_offset.expected !== undefined;

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
                <td>G{result.wcs_offset.work_offset}</td>
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
              const actual = result.wcs_offset!.actual[axis as keyof typeof result.wcs_offset.actual];
              const expected = result.wcs_offset!.expected[axis as keyof typeof result.wcs_offset.expected];
              const diff = result.wcs_offset!.difference[axis as keyof typeof result.wcs_offset.difference];
              const axisWithinTol = diff <= tolerance;
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

  const renderFooter = () => {
    if (uploadSuccess && deployedInfo) {
      // Success screen footer
      return (
        <div className="upload-actions-footer">
          <div className="footer-success">
            <div className="success-icon">✓</div>
            <div className="success-message">SUCCESSFULLY UPLOADED</div>
          </div>
          <div className="footer-actions">
            <button
              className="terminal-button cancel"
              onClick={handleClose}
            >
              {closeCountdown > 0 ? `[ AUTO-CLOSE ${closeCountdown}s ]` : '[ CLOSE ]'}
            </button>
            <button
              className="terminal-button primary"
              onClick={handleGoToFileManager}
            >
              [ GO TO FILE MANAGER ]
            </button>
          </div>
        </div>
      );
    }

    // Normal footer with O-number configuration
    return (
      <div className="upload-actions-footer">
        <div className="footer-config">
          <div className="footer-item">
            <span className="footer-label">MACHINE:</span>
            <span className="footer-value">{machineName}</span>
          </div>
          <div className="footer-item">
            <span className="footer-label">PATH:</span>
            <span className="footer-value">{machinePath}/</span>
          </div>
          <div className="footer-item">
            <span className="footer-label">O-NUMBER:</span>
            {isLoadingONumber ? (
              <span className="footer-value">Loading...</span>
            ) : (
              <div className="onumber-input-group">
                <input
                  type="text"
                  className="onumber-input"
                  value={customONumber}
                  onChange={(e) => setCustomONumber(e.target.value)}
                  disabled={isUploading}
                />
                {isReplacingExisting && replacementInfo && (
                  <span className="replacement-badge">
                    REPLACING {replacementInfo.original_filename}
                  </span>
                )}
              </div>
            )}
          </div>
        </div>
        <div className="footer-actions">
          <button
            className="terminal-button cancel"
            onClick={handleClose}
            disabled={isUploading}
          >
            [ CANCEL ]
          </button>
          <button
            className={`terminal-button ${result.valid ? 'primary' : 'warning'}`}
            onClick={performUpload}
            disabled={isUploading || isLoadingONumber || !customONumber}
          >
            {isUploading ? '[ UPLOADING... ]' : '[ UPLOAD ]'}
          </button>
        </div>
      </div>
    );
  };

  const renderProgramInfo = () => {
    const runtime = result.metadata.estimated_runtime_seconds;
    const hrs = runtime ? Math.floor(runtime / 3600) : 0;
    const mins = runtime ? Math.floor((runtime % 3600) / 60) : 0;
    const secs = runtime ? Math.floor(runtime % 60) : 0;
    const runtimeStr = runtime ? `${String(hrs).padStart(2, '0')}:${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}` : '--:--:--';

    return (
      <div className="program-info-summary">
        <div className="info-row">
          <span className="info-label">LINES:</span>
          <span className="info-value">{result.metadata.line_count}</span>
        </div>
        <div className="info-row">
          <span className="info-label">SIZE:</span>
          <span className="info-value">{(result.metadata.file_size / 1024).toFixed(1)} KB</span>
        </div>
        <div className="info-row">
          <span className="info-label">TOOLS:</span>
          <span className="info-value">{result.metadata.tool_count}</span>
        </div>
        <div className="info-row">
          <span className="info-label">RUNTIME:</span>
          <span className="info-value">{runtimeStr}</span>
        </div>
      </div>
    );
  };

  const validationStatusText = result.valid ? '✓ PASS' : '✕ FAIL';
  const validationStatusClass = result.valid ? 'text-success' : 'text-error';

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title={
        <div className="upload-title-container">
          <span>{filename}</span>
          <span className={`validation-badge ${validationStatusClass}`}>{validationStatusText}</span>
        </div>
      }
      footer={renderFooter()}
    >
      <div className="upload-confirmation">
        {!uploadSuccess ? (
          <>
            {/* Program Info Summary */}
            {renderProgramInfo()}

            {/* Validation sections */}
            {renderToolsSection()}
            {renderWCSSection()}

            {/* Upload Progress and Errors */}
            {uploadError && (
              <div className="error-message">
                ✕ {uploadError}
              </div>
            )}

            {isUploading && (
              <div className="upload-progress">
                <div className="progress-bar">
                  <div className="progress-fill" style={{ width: `${uploadProgress}%` }} />
                </div>
                <span className="progress-text">{uploadProgress}%</span>
              </div>
            )}
          </>
        ) : (
          <>
            {/* Success Screen */}
            <div className="success-section">
              <div className="success-details">
                <div className="detail-row">
                  <span className="label">O-NUMBER:</span>
                  <span className="value">{deployedInfo.onumber}</span>
                </div>
                <div className="detail-row">
                  <span className="label">MACHINE:</span>
                  <span className="value">{deployedInfo.machine}</span>
                </div>
                <div className="detail-row">
                  <span className="label">PATH:</span>
                  <span className="value">{deployedInfo.path}</span>
                </div>
                {deployedInfo.was_replacement && deployedInfo.replacement_details && (
                  <div className="detail-row replacement-info">
                    <span className="label">REPLACED:</span>
                    <span className="value">{deployedInfo.replacement_details.original_filename}</span>
                  </div>
                )}
              </div>
            </div>
          </>
        )}
      </div>
    </Modal>
  );
};
