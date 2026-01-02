import React, { useState, useEffect } from 'react';
import { API_BASE } from '../config/api';
import './ToolDetailModal.css';

interface OperationStats {
  operation_name: string | null;
  spindle_speed: number | null;
  feedrate_cutting: number | null;
  feedrate_plunge: number | null;
  feedrate_finish: number | null;
  feedrate_entry: number | null;
  feedrate_exit: number | null;
  feedrate_direct: number | null;
  feedrate_transition: number | null;
}

interface ProgramUsage {
  program_id: number;
  filename: string;
  version: number;
  production_runs: number;
  last_run: string | null;
  operations: OperationStats[];
}

interface AlarmSummary {
  alarm_code: string;
  alarm_message: string;
  occurrences: number;
  last_occurrence: string | null;
}

interface ToolDetail {
  tool_number: number;
  specifications: {
    diameter_range: [number, number];
    descriptions: string[];
    length_range: [number, number] | null;
  };
  usage_statistics: {
    total_programs: number;
    total_production_runs: number;
    estimated_runtime_seconds: number;
    total_parts_produced: number;
  };
  machines: Array<{
    machine_id: number;
    machine_name: string;
    production_runs: number;
    runtime_seconds: number;
  }>;
  operations: OperationStats[];
  programs: ProgramUsage[];
  alarms: AlarmSummary[];
}

interface ToolDetailModalProps {
  toolNumber: number;
  onClose: () => void;
}

export const ToolDetailModal: React.FC<ToolDetailModalProps> = ({
  toolNumber,
  onClose,
}) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [toolDetail, setToolDetail] = useState<ToolDetail | null>(null);

  useEffect(() => {
    const fetchToolDetail = async () => {
      setLoading(true);
      setError(null);

      try {
        const response = await fetch(`${API_BASE}/tools/${toolNumber}`);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data: ToolDetail = await response.json();
        setToolDetail(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch tool detail');
      } finally {
        setLoading(false);
      }
    };

    fetchToolDetail();
  }, [toolNumber]);

  // Handle close (Escape key or click outside)
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('keydown', handleEscape);
    document.body.style.overflow = 'hidden'; // Prevent background scrolling

    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = 'unset';
    };
  }, [onClose]);

  const formatToolNumber = (num: number): string => {
    return `T${num.toString().padStart(2, '0')}`;
  };

  const formatRuntime = (seconds: number): string => {
    if (seconds === 0) return '0m';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    if (hours > 0) return `${hours}h ${minutes}m`;
    return `${minutes}m`;
  };

  const formatValue = (value: number | null): string => {
    if (value === null || value === undefined) return '—';
    return value.toFixed(1);
  };

  const renderContent = () => {
    if (loading) {
      return (
        <div className="tool-detail-loading">
          <div className="loading-text">LOADING<span className="loading-dots">...</span></div>
        </div>
      );
    }

    if (error) {
      return (
        <div className="tool-detail-error">
          <div className="error-message">ERROR: {error}</div>
          <button className="retry-button" onClick={() => window.location.reload()}>
            RETRY
          </button>
        </div>
      );
    }

    if (!toolDetail) {
      return <div className="tool-detail-empty">No tool data available</div>;
    }

    return (
      <>
        {/* Specifications Section */}
        <div className="detail-section">
          <div className="detail-section-header">
            ┌─ SPECIFICATIONS {'─'.repeat(80)}┐
          </div>
          <div className="detail-section-content">
            <div className="spec-grid">
              <div className="spec-item">
                <span className="spec-label">DIAMETER:</span>
                <span className="spec-value">
                  {toolDetail.specifications.diameter_range[0].toFixed(3)}"
                  {toolDetail.specifications.diameter_range[0] !== toolDetail.specifications.diameter_range[1] &&
                    ` - ${toolDetail.specifications.diameter_range[1].toFixed(3)}"`}
                </span>
                {/* TODO: Add units support when tool detail API includes units */}
              </div>
              {toolDetail.specifications.length_range && (
                <div className="spec-item">
                  <span className="spec-label">LENGTH:</span>
                  <span className="spec-value">
                    {toolDetail.specifications.length_range[0].toFixed(3)}"
                    {toolDetail.specifications.length_range[0] !== toolDetail.specifications.length_range[1] &&
                      ` - ${toolDetail.specifications.length_range[1].toFixed(3)}"`}
                  </span>
                </div>
              )}
              <div className="spec-item">
                <span className="spec-label">TYPE:</span>
                <span className="spec-value">{toolDetail.specifications.descriptions.join(', ')}</span>
              </div>
            </div>
          </div>
          <div className="detail-section-footer">
            └{'─'.repeat(99)}┘
          </div>
        </div>

        {/* Usage Statistics Section */}
        <div className="detail-section">
          <div className="detail-section-header">
            ┌─ USAGE STATISTICS {'─'.repeat(77)}┐
          </div>
          <div className="detail-section-content">
            <div className="spec-grid">
              <div className="spec-item">
                <span className="spec-label">PROGRAMS:</span>
                <span className="spec-value text-info">{toolDetail.usage_statistics.total_programs}</span>
              </div>
              <div className="spec-item">
                <span className="spec-label">RUNS:</span>
                <span className="spec-value text-info">{toolDetail.usage_statistics.total_production_runs}</span>
              </div>
              <div className="spec-item">
                <span className="spec-label">RUNTIME:</span>
                <span className="spec-value">{formatRuntime(toolDetail.usage_statistics.estimated_runtime_seconds)}</span>
              </div>
              <div className="spec-item">
                <span className="spec-label">PARTS:</span>
                <span className="spec-value">{toolDetail.usage_statistics.total_parts_produced.toLocaleString()}</span>
              </div>
            </div>
          </div>
          <div className="detail-section-footer">
            └{'─'.repeat(99)}┘
          </div>
        </div>

        {/* Programs Section */}
        {toolDetail.programs.length > 0 && (
          <div className="detail-section">
            <div className="detail-section-header">
              ┌─ PROGRAMS & OPERATIONS {'─'.repeat(74)}┐
            </div>
            <div className="detail-section-content no-padding">
              {toolDetail.programs.map((prog) => (
                <div key={prog.program_id} className="program-section">
                  <div className="program-header">
                    <span className="text-info">{prog.filename}</span>
                    <span className="text-dim"> v{prog.version}</span>
                    <span className="separator"> │ </span>
                    <span>RUNS: {prog.production_runs}</span>
                    <span className="separator"> │ </span>
                    <span className="text-dim">
                      LAST RUN: {prog.last_run ? new Date(prog.last_run).toLocaleString() : 'Never'}
                    </span>
                  </div>
                  {prog.operations.length > 0 && (
                    <table className="operations-table">
                      <thead>
                        <tr>
                          <th>OPERATION</th>
                          <th>SPINDLE</th>
                          <th>CUTTING</th>
                          <th>PLUNGE</th>
                          <th>FINISH</th>
                          <th>ENTRY</th>
                          <th>EXIT</th>
                          <th>DIRECT</th>
                          <th>TRANS</th>
                        </tr>
                      </thead>
                      <tbody>
                        {prog.operations.map((op, idx) => (
                          <tr key={idx}>
                            <td className="text-info">{op.operation_name || 'UNKNOWN'}</td>
                            <td>{formatValue(op.spindle_speed)}</td>
                            <td>{formatValue(op.feedrate_cutting)}</td>
                            <td>{formatValue(op.feedrate_plunge)}</td>
                            <td>{formatValue(op.feedrate_finish)}</td>
                            <td>{formatValue(op.feedrate_entry)}</td>
                            <td>{formatValue(op.feedrate_exit)}</td>
                            <td>{formatValue(op.feedrate_direct)}</td>
                            <td>{formatValue(op.feedrate_transition)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              ))}
            </div>
            <div className="detail-section-footer">
              └{'─'.repeat(99)}┘
            </div>
          </div>
        )}

        {/* Alarms Section */}
        {toolDetail.alarms.length > 0 && (
          <div className="detail-section">
            <div className="detail-section-header">
              ┌─ ALARM CORRELATION {'─'.repeat(77)}┐
            </div>
            <div className="detail-section-content no-padding">
              <table className="alarms-table">
                <thead>
                  <tr>
                    <th>CODE</th>
                    <th>MESSAGE</th>
                    <th>COUNT</th>
                    <th>LAST OCCURRENCE</th>
                  </tr>
                </thead>
                <tbody>
                  {toolDetail.alarms.map((alarm, idx) => (
                    <tr key={idx}>
                      <td className="text-warning">{alarm.alarm_code}</td>
                      <td>{alarm.alarm_message}</td>
                      <td className="text-center">{alarm.occurrences}</td>
                      <td className="text-dim">
                        {alarm.last_occurrence ? new Date(alarm.last_occurrence).toLocaleString() : 'Never'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="detail-section-footer">
              └{'─'.repeat(99)}┘
            </div>
          </div>
        )}
      </>
    );
  };

  return (
    <div className="tool-detail-modal-overlay" onClick={onClose}>
      <div className="tool-detail-modal" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="tool-detail-modal-header">
          <h2 className="tool-detail-modal-title">
            {formatToolNumber(toolNumber)}
            {toolDetail && `: ${toolDetail.specifications.descriptions[0]}`}
          </h2>
          <button className="tool-detail-modal-close" onClick={onClose}>
            ✕
          </button>
        </div>

        {/* Content Area */}
        <div className="tool-detail-modal-content">
          {renderContent()}
        </div>
      </div>
    </div>
  );
};
