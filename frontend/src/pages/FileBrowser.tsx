import React, { useState, useEffect } from 'react';
import { StatusIndicator } from '../components/ui';
import './FileBrowser.css';
import { API_BASE_URL } from '../config/api';

interface Program {
  name: string;
  size: number;
  modified: string;
  is_directory: boolean;
  path: string;
}

interface Machine {
  id: number;
  name: string;
  ip_address: string;
  path?: string;
}

interface ViewData {
  file_path: string;
  content: string;
  size: number;
  lines: number;
}

interface FileMetadata {
  file_path: string;
  tools: number[];
  runtime_seconds: number;
  has_errors: boolean;
}

export const FileBrowser: React.FC = () => {
  const [machines, setMachines] = useState<Machine[]>([]);
  const [selectedMachineId, setSelectedMachineId] = useState<number | null>(null);
  const [programs, setPrograms] = useState<Program[]>([]);
  const [selectedProgram, setSelectedProgram] = useState<Program | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentPath, setCurrentPath] = useState<string | null>(null);
  const [pathLoading, setPathLoading] = useState(false);
  const [previewLines, setPreviewLines] = useState<string[]>([]);
  const [viewModalOpen, setViewModalOpen] = useState(false);
  const [viewModalContent, setViewModalContent] = useState<ViewData | null>(null);
  const [viewModalLoading, setViewModalLoading] = useState(false);
  const [fileMetadata, setFileMetadata] = useState<FileMetadata | null>(null);
  const [metadataLoading, setMetadataLoading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<{ fileName: string; percent: number } | null>(null);
  const [highlightedFile, setHighlightedFile] = useState<string | null>(null);
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  // Fetch machines on mount and auto-select first one
  useEffect(() => {
    fetch('${API_BASE_URL}/api/machines')
      .then(res => res.json())
      .then(data => {
        setMachines(data);
        // Auto-select first machine, path effect will handle loading the correct path
        if (data.length > 0) {
          setSelectedMachineId(data[0].id);
        }
      })
      .catch(err => console.error('Error fetching machines:', err));
  }, []);

  // Set path when machine changes - fetch fresh machine data to ensure we have latest config
  useEffect(() => {
    if (selectedMachineId === null) return;

    // Immediately clear path and set loading before any async operations
    setPathLoading(true);
    setCurrentPath(null);

    // Fetch fresh machine data to ensure we have the latest path configuration
    const controller = new AbortController();
    fetch(`${API_BASE_URL}/api/machines/${selectedMachineId}`, {
      signal: controller.signal,
    })
      .then(res => res.json())
      .then(machineData => {
        const newPath = machineData.path || '/';
        console.log(`[PATH-EFFECT] Machine ${selectedMachineId} fetched. path: '${newPath}'`);
        setCurrentPath(newPath);
        setPathLoading(false);
      })
      .catch(err => {
        if (err.name !== 'AbortError') {
          console.error(`[PATH-EFFECT] Error fetching machine ${selectedMachineId}:`, err);
          setCurrentPath('/');
          setPathLoading(false);
        }
      });

    return () => controller.abort();
  }, [selectedMachineId]);

  // Fetch programs when machine or path changes
  useEffect(() => {
    // Don't fetch if path is null OR if we're still loading the path
    if (selectedMachineId === null || currentPath === null || pathLoading) {
      return;
    }

    setLoading(true);
    setError(null);
    setPrograms([]);
    setSelectedProgram(null);

    const url = `${API_BASE_URL}/api/machines/${selectedMachineId}/programs?path=${encodeURIComponent(currentPath)}`;

    const controller = new AbortController();
    const fetchMachineId = selectedMachineId;
    const fetchPath = currentPath;

    fetch(url, { signal: controller.signal })
      .then(res => {
        if (!res.ok) {
          return res.json().then(data => {
            throw new Error(data.detail || `HTTP ${res.status}`);
          }).catch(() => {
            throw new Error(`HTTP ${res.status}`);
          });
        }
        return res.json();
      })
      .then(data => {
        // Only update if this fetch is still relevant (machine and path haven't changed)
        if (fetchMachineId === selectedMachineId && fetchPath === currentPath) {
          console.log(`[FETCH] Received ${data.programs?.length || 0} programs`);
          setPrograms(data.programs || []);
          setLoading(false);
        }
      })
      .catch(err => {
        if (err.name !== 'AbortError') {
          console.error('Error fetching programs:', err);
          const errorMsg = err.message || 'Unknown error';
          if (errorMsg.includes('timeout')) {
            setError('FTP connection timeout - check machine network connectivity');
          } else if (errorMsg.includes('ConnectionReset') || errorMsg === '') {
            setError('FTP server connection refused - verify machine FTP service is running');
          } else {
            setError(`Error: ${errorMsg}`);
          }
          setLoading(false);
        }
      });

    return () => controller.abort();
  }, [selectedMachineId, currentPath, pathLoading]);

  // Fetch preview and metadata when a .nc file is selected
  useEffect(() => {
    if (selectedProgram && selectedProgram.name.toUpperCase().endsWith('.NC') && !selectedProgram.is_directory) {
      fetchFilePreview(selectedProgram);
      fetchFileMetadata(selectedProgram);
    } else {
      setPreviewLines([]);
      setFileMetadata(null);
    }
  }, [selectedProgram]);

  const selectedMachine = machines.find(m => m.id === selectedMachineId);

  const formatBytes = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 10) / 10 + ' ' + sizes[i];
  };

  const formatDate = (dateStr: string) => {
    try {
      const date = new Date(dateStr);
      return date.toLocaleString('en-US', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return dateStr;
    }
  };

  const formatRuntime = (seconds: number) => {
    if (!seconds) return '─ unknown ─';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  // Animated ASCII progress bar during metadata parsing
  const [progressState, setProgressState] = React.useState(0);

  React.useEffect(() => {
    if (!metadataLoading) return;

    const interval = setInterval(() => {
      setProgressState(prev => (prev + 1) % 8);
    }, 900);

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

  const handleItemClick = (program: Program) => {
    if (program.is_directory) {
      // Navigate into directory
      if (program.name === '..') {
        // Go up one level
        const parentPath = (currentPath || '/').split('/').slice(0, -1).join('/') || '/';
        console.log(`[NAVIGATE] Going up: '${currentPath}' -> '${parentPath}'`);
        setCurrentPath(parentPath);
      } else {
        // Navigate into subdirectory
        const basePath = currentPath || '/';
        const newPath = basePath === '/' ? `/${program.name}` : `${basePath}/${program.name}`;
        console.log(`[NAVIGATE] Going down: '${basePath}' + '${program.name}' -> '${newPath}'`);
        setCurrentPath(newPath);
      }
    } else {
      // Select file to show details
      setSelectedProgram(program);
    }
  };

  const handleDownload = async (program: Program) => {
    if (!selectedMachineId || !currentPath) return;

    try {
      const filePath = `${currentPath}${currentPath === '/' ? '' : '/'}${program.name}`;
      const url = `${API_BASE_URL}/api/machines/${selectedMachineId}/download?file_path=${encodeURIComponent(filePath)}`;

      const response = await fetch(url);
      if (!response.ok) {
        try {
          const errorData = await response.json();
          throw new Error(errorData.detail || `HTTP ${response.status}`);
        } catch {
          throw new Error(`HTTP ${response.status}`);
        }
      }

      // Create blob and download
      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      link.download = program.name;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);
    } catch (err) {
      console.error('Download error:', err);
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(`Download failed: ${errorMessage}`);
    }
  };

  const fetchFilePreview = async (program: Program) => {
    if (!selectedMachineId || !currentPath) return;

    try {
      const filePath = `${currentPath}${currentPath === '/' ? '' : '/'}${program.name}`;
      const url = `${API_BASE_URL}/api/machines/${selectedMachineId}/view?file_path=${encodeURIComponent(filePath)}`;

      const response = await fetch(url);
      if (!response.ok) {
        try {
          const errorData = await response.json();
          throw new Error(errorData.detail || `HTTP ${response.status}`);
        } catch {
          throw new Error(`HTTP ${response.status}`);
        }
      }

      const data: ViewData = await response.json();
      const lines = data.content.split('\n');
      setPreviewLines(lines.slice(0, 50));
    } catch (err) {
      console.error('Preview error:', err);
      setPreviewLines(['Error loading preview']);
    }
  };

  const fetchFileMetadata = async (program: Program) => {
    if (!selectedMachineId || !currentPath) return;

    setMetadataLoading(true);
    try {
      const filePath = `${currentPath}${currentPath === '/' ? '' : '/'}${program.name}`;
      const url = `${API_BASE_URL}/api/machines/${selectedMachineId}/metadata?file_path=${encodeURIComponent(filePath)}`;

      const response = await fetch(url);
      if (!response.ok) {
        try {
          const errorData = await response.json();
          throw new Error(errorData.detail || `HTTP ${response.status}`);
        } catch {
          throw new Error(`HTTP ${response.status}`);
        }
      }

      const data: FileMetadata = await response.json();
      setFileMetadata(data);
    } catch (err) {
      console.error('Metadata error:', err);
      setFileMetadata(null);
    } finally {
      setMetadataLoading(false);
    }
  };

  const handleViewCode = async (program: Program) => {
    if (!selectedMachineId || !currentPath) return;

    setViewModalLoading(true);
    try {
      const filePath = `${currentPath}${currentPath === '/' ? '' : '/'}${program.name}`;
      const url = `${API_BASE_URL}/api/machines/${selectedMachineId}/view?file_path=${encodeURIComponent(filePath)}`;

      const response = await fetch(url);
      if (!response.ok) {
        try {
          const errorData = await response.json();
          throw new Error(errorData.detail || `HTTP ${response.status}`);
        } catch {
          throw new Error(`HTTP ${response.status}`);
        }
      }

      const data: ViewData = await response.json();
      setViewModalContent(data);
      setViewModalOpen(true);
    } catch (err) {
      console.error('View error:', err);
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setError(`View failed: ${errorMessage}`);
    } finally {
      setViewModalLoading(false);
    }
  };

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !selectedMachineId || !currentPath) return;

    const uploadPath = currentPath === '/' ? `/${file.name}` : `${currentPath}/${file.name}`;
    const url = `${API_BASE_URL}/api/machines/${selectedMachineId}/upload?file_path=${encodeURIComponent(uploadPath)}`;

    // Show upload progress entry in the file list
    setUploadProgress({ fileName: file.name, percent: 0 });
    setError(null);

    const xhr = new XMLHttpRequest();

    // Track upload progress
    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable) {
        const percentComplete = Math.round((e.loaded / e.total) * 100);
        setUploadProgress({ fileName: file.name, percent: percentComplete });
      }
    });

    // Handle completion
    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        setUploadProgress(null);
        setError(null);
        // Highlight the uploaded file for 5 seconds
        setHighlightedFile(file.name);
        setTimeout(() => setHighlightedFile(null), 5000);
        // Refresh the file list
        const programsUrl = `${API_BASE_URL}/api/machines/${selectedMachineId}/programs?path=${encodeURIComponent(currentPath)}`;
        fetch(programsUrl)
          .then(res => res.json())
          .then(data => {
            setPrograms(data.programs || []);
          })
          .catch(err => console.error('Error refreshing programs:', err));
      } else {
        try {
          const response = JSON.parse(xhr.responseText);
          const errorMsg = response.detail || `HTTP ${xhr.status}`;
          setError(`Upload failed: ${errorMsg}`);
        } catch {
          setError(`Upload failed: HTTP ${xhr.status}`);
        }
        setUploadProgress(null);
      }
    });

    // Handle errors
    xhr.addEventListener('error', () => {
      setError('Upload failed: Network error');
      setUploadProgress(null);
    });

    xhr.addEventListener('abort', () => {
      setError('Upload cancelled');
      setUploadProgress(null);
    });

    // Send the file
    const formData = new FormData();
    formData.append('file', file);
    xhr.open('POST', url);
    xhr.send(formData);

    // Reset input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // Sort and prepare display list
  const displayPrograms = (() => {
    // Separate directories and files
    const directories = programs.filter(p => p.is_directory).sort((a, b) => a.name.localeCompare(b.name));
    const files = programs.filter(p => !p.is_directory).sort((a, b) => a.name.localeCompare(b.name));

    // Combine: directories first, then files
    const sorted = [...directories, ...files];

    // Add parent directory entry at the top if not at root
    return currentPath !== '/'
      ? [{ name: '..', size: 0, modified: '', is_directory: true, path: '..' }, ...sorted]
      : sorted;
  })();

  return (
    <div className="file-browser">
      {/* Header */}
      <div className="file-browser-header">
        <div className="header-title">
          <span className="text-glow-strong">FILE MANAGER</span>
        </div>
        <div className="header-actions">
          <button
            className="terminal-button primary"
            onClick={handleUploadClick}
            disabled={uploadProgress !== null || !selectedMachineId}
          >
            [ UPLOAD ]
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".nc"
            style={{ display: 'none' }}
            onChange={handleFileSelect}
          />
        </div>
      </div>

      <div className="file-browser-divider">
        ╠{'═'.repeat(100)}╣
      </div>

      {/* Machine Selector */}
      <div className="machine-selector-bar">
        <label className="selector-label">MACHINE:</label>
        <select
          className="terminal-select"
          value={selectedMachineId || ''}
          onChange={(e) => setSelectedMachineId(Number(e.target.value))}
        >
          {machines.map(machine => (
            <option key={machine.id} value={machine.id}>
              {machine.name} ({machine.ip_address})
            </option>
          ))}
        </select>
        {selectedMachine && (
          <span className="machine-status">
            <StatusIndicator status="online" label="" />
          </span>
        )}
      </div>

      <div className="file-browser-content">
        {/* Programs List */}
        <div className="programs-panel">
          <div className="panel-header">
            ┌─ NC PROGRAMS (/CNC_MEM/) {'─'.repeat(50)}┐
          </div>

          {loading && (
            <div className="panel-loading">
              <span className="pulse">LOADING PROGRAMS...</span>
            </div>
          )}

          {error && (
            <div className="panel-error text-error">
              ERROR: {error}
            </div>
          )}

          {!loading && !error && programs.length === 0 && (
            <div className="panel-empty text-muted">
              NO PROGRAMS FOUND
            </div>
          )}

          {!loading && !error && programs.length > 0 && (
            <div className="programs-table">
              <div className="table-header">
                <div className="col-name">NAME</div>
                <div className="col-size">SIZE</div>
                <div className="col-modified">MODIFIED</div>
                <div className="col-actions">ACTIONS</div>
              </div>
              <div className="table-divider">
                ├{'─'.repeat(80)}┤
              </div>
              <div className="table-body">
                {uploadProgress && (
                  <div className="table-row upload-progress-row">
                    <div className="col-name">
                      {uploadProgress.fileName}
                    </div>
                    <div className="col-size"></div>
                    <div className="col-modified">
                      <div className="upload-progress-bar-container">
                        <div
                          className="upload-progress-bar-fill"
                          style={{ width: `${uploadProgress.percent}%` }}
                        ></div>
                      </div>
                      <span className="upload-progress-text">{uploadProgress.percent}%</span>
                    </div>
                    <div className="col-actions"></div>
                  </div>
                )}
                {displayPrograms.map((program, idx) => (
                  <div
                    key={idx}
                    className={`table-row ${selectedProgram?.name === program.name ? 'selected' : ''} ${highlightedFile === program.name ? 'uploaded' : ''}`}
                    onClick={() => handleItemClick(program)}
                  >
                    <div className="col-name">
                      {program.is_directory ? '/ ' : (selectedProgram?.name === program.name ? '► ' : '  ')}
                      {program.name}
                    </div>
                    <div className="col-size">{program.is_directory ? '<DIR>' : formatBytes(program.size)}</div>
                    <div className="col-modified">{formatDate(program.modified)}</div>
                    <div className="col-actions">
                      {!program.is_directory && (
                        <button
                          className="terminal-button-sm"
                          onClick={() => handleDownload(program)}
                        >
                          DL
                        </button>
                      )}
                      {program.is_directory && (
                        <span className="col-action-spacer"></span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
              <div className="table-footer">
                └{'─'.repeat(80)}┘
              </div>
              <div className="table-summary">
                {programs.length} PROGRAMS │ TOTAL: {formatBytes(programs.reduce((sum, p) => sum + p.size, 0))}
              </div>
            </div>
          )}
        </div>

        {/* Program Details Panel */}
        {selectedProgram && (
          <div className="details-panel">
            <div className="panel-header">
              ┌─ SELECTED: {selectedProgram.name} {'─'.repeat(30)}┐
            </div>
            <div className="details-content">
              <div className="detail-row">
                <span className="label">SIZE:</span>
                <span className="value">{formatBytes(selectedProgram.size)}</span>
              </div>
              <div className="detail-row">
                <span className="label">MODIFIED:</span>
                <span className="value">{formatDate(selectedProgram.modified)}</span>
              </div>
              <div className="detail-row">
                <span className="label">TOOLS:</span>
                <span className={`value ${metadataLoading ? 'text-muted' : fileMetadata?.tools && fileMetadata.tools.length > 0 ? '' : 'text-muted'}`}>
                  {metadataLoading ? renderProgressBar() : fileMetadata?.tools && fileMetadata.tools.length > 0
                    ? fileMetadata.tools.join(', ')
                    : '─ none detected ─'}
                </span>
              </div>
              <div className="detail-row">
                <span className="label">RUNTIME:</span>
                <span className={`value ${metadataLoading ? 'text-muted' : fileMetadata?.runtime_seconds ? '' : 'text-muted'}`}>
                  {metadataLoading ? renderProgressBar() : formatRuntime(fileMetadata?.runtime_seconds || 0)}
                </span>
              </div>

              <div className="detail-actions">
                <button
                  className="terminal-button"
                  onClick={() => handleDownload(selectedProgram)}
                >
                  [ DOWNLOAD ]
                </button>
                {selectedProgram.name.toUpperCase().endsWith('.NC') && (
                  <button
                    className="terminal-button"
                    onClick={() => handleViewCode(selectedProgram)}
                  >
                    [ VIEW CODE ]
                  </button>
                )}
              </div>

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
        )}
      </div>

      {/* Footer */}
      <div className="file-browser-footer">
        <div className="file-browser-divider">
          ╠{'═'.repeat(100)}╣
        </div>
        <div className="command-line">
          <span className="prompt">&gt;</span>
          <span>
            {selectedMachine ? `VIEWING: ${selectedMachine.name}` : 'NO MACHINE SELECTED'}
          </span>
          <span className="separator">│</span>
          <span className="text-dim">PROGRAMS: {programs.length}</span>
        </div>
      </div>

      {/* View Modal */}
      {viewModalOpen && (
        <div className="modal-overlay" onClick={() => setViewModalOpen(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <span className="modal-title">
                {viewModalContent?.file_path || 'FILE VIEWER'}
              </span>
              <button
                className="modal-close"
                onClick={() => setViewModalOpen(false)}
              >
                ✕
              </button>
            </div>

            {viewModalLoading && (
              <div className="modal-loading">
                <span className="pulse">LOADING...</span>
              </div>
            )}

            {!viewModalLoading && viewModalContent && (
              <div className="modal-body">
                <div className="file-stats">
                  <span>SIZE: {(viewModalContent.size / 1024).toFixed(2)} KB</span>
                  <span>│</span>
                  <span>LINES: {viewModalContent.lines}</span>
                </div>
                <div className="code-viewer">
                  {viewModalContent.content.split('\n').map((line, idx) => (
                    <div key={idx} className="code-line">
                      <span className="line-number">{idx + 1}</span>
                      <span className="line-content">{line || ' '}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="modal-footer">
              <button className="terminal-button" onClick={() => setViewModalOpen(false)}>
                [ CLOSE ]
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
