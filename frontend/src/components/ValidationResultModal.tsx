import React, { useState, useEffect, useRef } from 'react';
import { Modal } from './ui/Modal';
import './ValidationResultModal.css';
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

interface ValidationResultModalProps {
  isOpen: boolean;
  onClose: () => void;
  result: ValidationResult | null;
  filename: string;
  // Upload props
  machineId?: number;
  machineName?: string;
  machinePath?: string;
  fileContent?: string;
}

export const ValidationResultModal: React.FC<ValidationResultModalProps> = ({
  isOpen,
  onClose,
  result,
  filename,
  machineId,
  machineName,
  machinePath,
  fileContent,
}) => {
  const [customONumber, setCustomONumber] = useState('O2000.nc');
  const [isReplacingExisting, setIsReplacingExisting] = useState(false);
  const [replacementInfo, setReplacementInfo] = useState<any>(null);
  const [isLoadingONumber, setIsLoadingONumber] = useState(false);
  const [showConfirmationModal, setShowConfirmationModal] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [deployedInfo, setDeployedInfo] = useState<any>(null);
  const [closeCountdown, setCloseCountdown] = useState(0);
  const [autoCloseDisabled, setAutoCloseDisabled] = useState(false);
  const onCloseRef = useRef(onClose);

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
    if (uploadSuccess && !autoCloseDisabled) {
      setCloseCountdown(5);

      const countdownInterval = setInterval(() => {
        setCloseCountdown((prev) => {
          if (prev <= 1) {
            clearInterval(countdownInterval);
            // Reset upload state before closing
            setUploadSuccess(false);
            setUploadProgress(0);
            setUploadError(null);
            setIsUploading(false);
            setShowConfirmationModal(false);
            setCustomONumber('O2000.nc');
            setAutoCloseDisabled(false);
            setDeployedInfo(null);
            // Then call parent close
            onCloseRef.current();
            return 0;
          }
          return prev - 1;
        });
      }, 1000);

      return () => clearInterval(countdownInterval);
    }
  }, [uploadSuccess, autoCloseDisabled]);

  // Reset all upload state when modal closes
  useEffect(() => {
    if (!isOpen) {
      setUploadSuccess(false);
      setUploadProgress(0);
      setUploadError(null);
      setIsUploading(false);
      setShowConfirmationModal(false);
      setCustomONumber('O2000.nc');
      setAutoCloseDisabled(false);
      setDeployedInfo(null);
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

      console.log('Fetched O-number data:', data);

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

  const handleUploadClick = () => {
    if (!result) return;

    if (!result.valid) {
      setShowConfirmationModal(true);
    } else {
      performUpload();
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
    setShowConfirmationModal(false);

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

    } catch (error) {
      console.error('Upload error:', error);
      setUploadError(error instanceof Error ? error.message : 'Upload failed');
    } finally {
      setIsUploading(false);
    }
  };

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
    if (!machineId) return undefined;

    return (
      <div className="upload-actions-footer">
        <div className="footer-config">
          <div className="footer-item">
            <span className="footer-label">MACHINE:</span>
            <span className="footer-value">
              {uploadSuccess && deployedInfo ? deployedInfo.machine : machineName}
            </span>
          </div>
          <div className="footer-item">
            <span className="footer-label">PATH:</span>
            <span className="footer-value">
              {uploadSuccess && deployedInfo ? `${deployedInfo.path}/` : `${machinePath}/`}
            </span>
          </div>
          <div className="footer-item">
            <span className="footer-label">O-NUMBER:</span>
            {isLoadingONumber ? (
              <span className="footer-value">Loading...</span>
            ) : isUploading || uploadSuccess ? (
              <span className="footer-value">{customONumber}</span>
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
          {uploadSuccess && deployedInfo ? (
            <>
              {!autoCloseDisabled && (
                <button
                  className="terminal-button cancel"
                  onClick={() => setAutoCloseDisabled(true)}
                  title="Click to pause auto-close"
                >
                  [ PAUSE ]
                </button>
              )}
              <button
                className="terminal-button primary"
                onClick={onClose}
                disabled={false}
                title={autoCloseDisabled ? 'Click to close' : 'Close now or wait for auto-close'}
              >
                {autoCloseDisabled ? '[ CLOSE ]' : `[ AUTOCLOSE ${closeCountdown}s ]`}
              </button>
            </>
          ) : (
            <>
              <button
                className="terminal-button cancel"
                onClick={onClose}
                disabled={isUploading}
              >
                [ CANCEL ]
              </button>
              <button
                className={`terminal-button ${result?.valid ? 'primary' : 'warning'}`}
                onClick={handleUploadClick}
                disabled={isUploading || isLoadingONumber || !customONumber}
              >
                {isUploading ? '[ UPLOADING... ]' : '[ UPLOAD ]'}
              </button>
            </>
          )}
        </div>
      </div>
    );
  };

  return (
    <>
      <Modal
        isOpen={isOpen && !showConfirmationModal}
        onClose={onClose}
        title={`VALIDATION - ${filename}`}
        footer={renderFooter()}
      >
        <div className="validation-result">
          {/* Overall Status */}
          <div className={`validation-status ${result.valid ? 'text-success' : 'text-error'}`}>
            <div className="status-text">
              {result.valid ? '✓ VALIDATION PASSED' : '✕ VALIDATION FAILED'}
            </div>
          </div>

          {/* Errors - Display immediately after status */}
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

          {/* Upload Progress and Errors */}
          {machineId && !uploadSuccess && (
            <>
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
          )}

        </div>
      </Modal>

      {/* Confirmation Modal */}
      {showConfirmationModal && result && !result.valid && (
        <div className="confirmation-overlay">
          <div className="confirmation-modal">
            <div className="confirmation-header">
              ⚠ CONFIRM UPLOAD DESPITE VALIDATION FAILURES
            </div>

            <div className="confirmation-body">
              <p className="confirmation-message">
                The following validation errors were found.
                Are you sure you want to upload this file to the machine?
              </p>

              <div className="confirmation-errors">
                <div className="errors-header">Validation Errors:</div>
                {result.errors.map((error, idx) => (
                  <div key={idx} className="error-item">
                    • {error}
                  </div>
                ))}

                {result.warnings.length > 0 && (
                  <>
                    <div className="warnings-header">Warnings:</div>
                    {result.warnings.map((warning, idx) => (
                      <div key={idx} className="warning-item">
                        • {warning}
                      </div>
                    ))}
                  </>
                )}
              </div>

              <div className="confirmation-details">
                <div className="detail-row">
                  <span className="label">Destination:</span>
                  <span className="value">{machinePath}/{customONumber}</span>
                </div>
                <div className="detail-row">
                  <span className="label">Machine:</span>
                  <span className="value">{machineName}</span>
                </div>
              </div>
            </div>

            <div className="confirmation-actions">
              <button
                className="terminal-button cancel"
                onClick={() => setShowConfirmationModal(false)}
              >
                [ GO BACK ]
              </button>
              <button
                className="terminal-button warning"
                onClick={performUpload}
              >
                [ CONFIRM UPLOAD ]
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
