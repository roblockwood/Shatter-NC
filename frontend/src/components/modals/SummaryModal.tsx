import React, { useState, useEffect } from 'react';
import { summaryApi } from '../../api/summary';
import type { RunningSummary } from '../../api/summary';
import { RunningSummaryRow } from './summary/RunningSummaryRow';
import './SummaryModal.css';

interface SummaryModalProps {
  isOpen: boolean;
  onClose: () => void;
  summaryType: 'running';
}

export const SummaryModal: React.FC<SummaryModalProps> = ({
  isOpen,
  onClose,
}) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [timeRange, setTimeRange] = useState('24h');
  const [runningData, setRunningData] = useState<RunningSummary | null>(null);

  useEffect(() => {
    if (!isOpen) return;

    const fetchData = async (isInitial: boolean = false) => {
      if (isInitial) {
        setLoading(true);
      }
      setError(null);

      try {
        const runningResponse = await summaryApi.getRunning(timeRange);
        setRunningData(runningResponse);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch summary data');
      } finally {
        if (isInitial) {
          setLoading(false);
        }
      }
    };

    fetchData(true);
    const pollInterval = setInterval(() => fetchData(false), 2000);
    return () => clearInterval(pollInterval);
  }, [isOpen, timeRange]);

  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      document.body.style.overflow = 'hidden';
    }

    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const renderContent = () => {
    if (loading) {
      return (
        <div className="summary-loading">
          <div className="loading-text">LOADING<span className="loading-dots">...</span></div>
        </div>
      );
    }

    if (error) {
      return (
        <div className="summary-error">
          <div className="error-message">ERROR: {error}</div>
        </div>
      );
    }

    if (!runningData || runningData.machines.length === 0) {
      return <div className="summary-empty">No running data available</div>;
    }

    return runningData.machines.map((machine) => (
      <RunningSummaryRow
        key={machine.machine_id}
        machine={machine}
        compact={false}
        timeRange={timeRange as '1h' | '8h' | '24h' | '7d'}
      />
    ));
  };

  return (
    <div className="summary-modal-overlay" onClick={onClose}>
      <div className="summary-modal summary-modal-running" onClick={(e) => e.stopPropagation()}>
        <div className="summary-modal-header">
          <h2 className="summary-modal-title">{`RUNNING MACHINES (${timeRange.toUpperCase()})`}</h2>
          {!loading && !error && (
            <div className="summary-modal-header-controls">
              {(['1h', '8h', '24h', '7d'] as const).map((range) => (
                <button
                  key={range}
                  className={`time-range-btn ${timeRange === range ? 'active' : ''}`}
                  onClick={() => setTimeRange(range)}
                  disabled={loading}
                >
                  [{range.toUpperCase()}]
                </button>
              ))}
            </div>
          )}
          <button className="summary-modal-close" onClick={onClose}>
            ✕
          </button>
        </div>

        {!loading && !error && (
          <div className="summary-headers">
            {['MACHINE', 'RUN TIME', 'PERCENTAGE', 'POLLING'].map((header) => (
              <div key={header} className="summary-header">
                {header}
              </div>
            ))}
          </div>
        )}

        <div className="summary-modal-content">{renderContent()}</div>
      </div>
    </div>
  );
};
