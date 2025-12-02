import React, { useState, useEffect } from 'react';
import { StatusIndicator } from '../components/ui';
import './FileBrowser.css';

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
}

interface ViewData {
  file_path: string;
  content: string;
  size: number;
  lines: number;
}

export const FileBrowser: React.FC = () => {
  const [machines, setMachines] = useState<Machine[]>([]);
  const [selectedMachineId, setSelectedMachineId] = useState<number | null>(null);
  const [programs, setPrograms] = useState<Program[]>([]);
  const [selectedProgram, setSelectedProgram] = useState<Program | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentPath, setCurrentPath] = useState<string>('/');
  const [previewLines, setPreviewLines] = useState<string[]>([]);
  const [viewModalOpen, setViewModalOpen] = useState(false);
  const [viewModalContent, setViewModalContent] = useState<ViewData | null>(null);
  const [viewModalLoading, setViewModalLoading] = useState(false);

  // Fetch machines on mount
  useEffect(() => {
    fetch('http://localhost:8000/api/machines')
      .then(res => res.json())
      .then(data => {
        setMachines(data);
        if (data.length > 0) {
          setSelectedMachineId(data[0].id);
        }
      })
      .catch(err => console.error('Error fetching machines:', err));
  }, []);

  // Fetch programs when machine or path changes
  useEffect(() => {
    if (selectedMachineId === null) return;

    setLoading(true);
    setError(null);
    setPrograms([]);
    setSelectedProgram(null);

    const url = `http://localhost:8000/api/machines/${selectedMachineId}/programs?path=${encodeURIComponent(currentPath)}`;
    fetch(url)
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
        console.log('Programs response:', data);
        setPrograms(data.programs || []);
        setLoading(false);
      })
      .catch(err => {
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
      });
  }, [selectedMachineId, currentPath]);

  // Reset path when machine changes
  useEffect(() => {
    setCurrentPath('/');
  }, [selectedMachineId]);

  // Fetch preview when a .nc file is selected
  useEffect(() => {
    if (selectedProgram && selectedProgram.name.toUpperCase().endsWith('.NC') && !selectedProgram.is_directory) {
      fetchFilePreview(selectedProgram);
    } else {
      setPreviewLines([]);
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

  const handleItemClick = (program: Program) => {
    if (program.is_directory) {
      // Navigate into directory
      if (program.name === '..') {
        // Go up one level
        const parentPath = currentPath.split('/').slice(0, -1).join('/') || '/';
        setCurrentPath(parentPath);
      } else {
        setCurrentPath(program.name);
      }
    } else {
      // Select file to show details
      setSelectedProgram(program);
    }
  };

  const handleDownload = async (program: Program) => {
    if (!selectedMachineId) return;

    try {
      const filePath = `${currentPath}${currentPath === '/' ? '' : '/'}${program.name}`;
      const url = `http://localhost:8000/api/machines/${selectedMachineId}/download?file_path=${encodeURIComponent(filePath)}`;

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
    if (!selectedMachineId) return;

    try {
      const filePath = `${currentPath}${currentPath === '/' ? '' : '/'}${program.name}`;
      const url = `http://localhost:8000/api/machines/${selectedMachineId}/view?file_path=${encodeURIComponent(filePath)}`;

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

  const handleViewCode = async (program: Program) => {
    if (!selectedMachineId) return;

    setViewModalLoading(true);
    try {
      const filePath = `${currentPath}${currentPath === '/' ? '' : '/'}${program.name}`;
      const url = `http://localhost:8000/api/machines/${selectedMachineId}/view?file_path=${encodeURIComponent(filePath)}`;

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
          <button className="terminal-button primary">
            [ UPLOAD ]
          </button>
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
                {displayPrograms.map((program, idx) => (
                  <div
                    key={idx}
                    className={`table-row ${selectedProgram?.name === program.name ? 'selected' : ''}`}
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
                <span className="value text-muted">─ parsing not yet implemented ─</span>
              </div>
              <div className="detail-row">
                <span className="label">RUNTIME:</span>
                <span className="value text-muted">─ parsing not yet implemented ─</span>
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
