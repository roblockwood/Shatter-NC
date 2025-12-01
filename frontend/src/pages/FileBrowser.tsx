import React, { useState, useEffect } from 'react';
import { StatusIndicator } from '../components/ui';
import './FileBrowser.css';

interface Program {
  name: string;
  size: number;
  modified: string;
}

interface Machine {
  id: number;
  name: string;
  ip_address: string;
}

export const FileBrowser: React.FC = () => {
  const [machines, setMachines] = useState<Machine[]>([]);
  const [selectedMachineId, setSelectedMachineId] = useState<number | null>(null);
  const [programs, setPrograms] = useState<Program[]>([]);
  const [selectedProgram, setSelectedProgram] = useState<Program | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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

  // Fetch programs when machine changes
  useEffect(() => {
    if (selectedMachineId === null) return;

    setLoading(true);
    setError(null);
    setPrograms([]);
    setSelectedProgram(null);

    fetch(`http://localhost:8000/api/machines/${selectedMachineId}/programs`)
      .then(res => {
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
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
        setError(`CNC FTP server offline or unreachable`);
        setLoading(false);
      });
  }, [selectedMachineId]);

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
                {programs.map((program, idx) => (
                  <div
                    key={idx}
                    className={`table-row ${selectedProgram?.name === program.name ? 'selected' : ''}`}
                    onClick={() => setSelectedProgram(program)}
                  >
                    <div className="col-name">
                      {selectedProgram?.name === program.name ? '► ' : '  '}
                      {program.name}
                    </div>
                    <div className="col-size">{formatBytes(program.size)}</div>
                    <div className="col-modified">{formatDate(program.modified)}</div>
                    <div className="col-actions">
                      <button className="terminal-button-sm">DL</button>
                      <button className="terminal-button-sm danger">DEL</button>
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
                <button className="terminal-button">[ DOWNLOAD ]</button>
                <button className="terminal-button">[ VIEW CODE ]</button>
                <button className="terminal-button danger">[ DELETE ]</button>
              </div>
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
    </div>
  );
};
