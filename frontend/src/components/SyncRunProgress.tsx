import React from 'react';
import type { FtpSyncRun } from '../api/ftpSync';

interface SyncRunProgressProps {
  run: FtpSyncRun;
}

export const SyncRunProgress: React.FC<SyncRunProgressProps> = ({ run }) => {
  const completed = run.success_files + run.skipped_files + run.conflict_files + run.failed_files;
  const pending = run.total_files - completed;
  const percentage = run.total_files > 0 ? Math.round((completed / run.total_files) * 100) : 0;

  // Determine status badge color and text
  const getStatusDisplay = () => {
    switch (run.status) {
      case 'queued':
      case 'in_progress':
      case 'processing':
        return { badge: '◯ In Progress', className: 'status-active', animated: true };
      case 'completed':
        return { badge: '✓ Completed', className: 'status-completed', animated: false };
      case 'interrupted':
        return { badge: '✗ Interrupted', className: 'status-interrupted', animated: false };
      case 'failed':
        return { badge: '⚠ Failed', className: 'status-failed', animated: false };
      default:
        return { badge: run.status, className: 'status-unknown', animated: false };
    }
  };

  const statusDisplay = getStatusDisplay();

  return (
    <div className="sync-run-progress">
      {/* Progress Bar */}
      <div className="progress-bar-container">
        <div className="progress-bar" style={{ width: '100%' }}>
          {/* Success segment (green) */}
          <div
            className="progress-segment success"
            style={{
              width: `${run.total_files > 0 ? (run.success_files / run.total_files) * 100 : 0}%`,
            }}
            title={`Success: ${run.success_files}`}
          />
          {/* Skipped segment (blue) */}
          <div
            className="progress-segment skipped"
            style={{
              width: `${run.total_files > 0 ? (run.skipped_files / run.total_files) * 100 : 0}%`,
            }}
            title={`Skipped: ${run.skipped_files}`}
          />
          {/* Conflict segment (yellow) */}
          <div
            className="progress-segment conflict"
            style={{
              width: `${run.total_files > 0 ? (run.conflict_files / run.total_files) * 100 : 0}%`,
            }}
            title={`Conflicts: ${run.conflict_files}`}
          />
          {/* Failed segment (red) */}
          <div
            className="progress-segment failed"
            style={{
              width: `${run.total_files > 0 ? (run.failed_files / run.total_files) * 100 : 0}%`,
            }}
            title={`Failed: ${run.failed_files}`}
          />
          {/* Pending segment (gray) */}
          <div
            className="progress-segment pending"
            style={{
              width: `${run.total_files > 0 ? (pending / run.total_files) * 100 : 0}%`,
            }}
            title={`Pending: ${pending}`}
          />
        </div>
      </div>

      {/* Stats Line */}
      <div className="progress-stats">
        <div className={`status-badge ${statusDisplay.className} ${statusDisplay.animated ? 'animated' : ''}`}>
          {statusDisplay.badge}
        </div>
        <span className="stats-text">
          {completed}/{run.total_files} ({percentage}%)
        </span>
        <span className="file-counts">
          ✓{run.success_files} ∘{run.skipped_files} ⚠{run.conflict_files} ✗{run.failed_files}
        </span>
      </div>
    </div>
  );
};
