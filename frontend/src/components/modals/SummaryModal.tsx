import React, { useState, useEffect } from 'react';
import { summaryApi } from '../../api/summary';
import type {
  RunningSummary,
  OnlineSummary,
  OfflineSummary,
} from '../../api/summary';
import { TimeRangeSelector } from './summary/TimeRangeSelector';
import { RunningSummaryRow } from './summary/RunningSummaryRow';
import { OnlineSummaryRow } from './summary/OnlineSummaryRow';
import { OfflineSummaryRow } from './summary/OfflineSummaryRow';
import './SummaryModal.css';

interface SummaryModalProps {
  isOpen: boolean;
  onClose: () => void;
  summaryType: 'running' | 'online' | 'offline';
}

export const SummaryModal: React.FC<SummaryModalProps> = ({
  isOpen,
  onClose,
  summaryType,
}) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [timeRange, setTimeRange] = useState('24h');

  // Data states
  const [runningData, setRunningData] = useState<RunningSummary | null>(null);
  const [onlineData, setOnlineData] = useState<OnlineSummary | null>(null);
  const [offlineData, setOfflineData] = useState<OfflineSummary | null>(null);

  // Fetch data based on summary type
  useEffect(() => {
    if (!isOpen) return;

    const fetchData = async () => {
      setLoading(true);
      setError(null);

      try {
        switch (summaryType) {
          case 'running':
            const runningResponse = await summaryApi.getRunning(timeRange);
            setRunningData(runningResponse);
            break;
          case 'online':
            const onlineResponse = await summaryApi.getOnline();
            setOnlineData(onlineResponse);
            break;
          case 'offline':
            const offlineResponse = await summaryApi.getOffline();
            setOfflineData(offlineResponse);
            break;
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch summary data');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [isOpen, summaryType, timeRange]);

  // Handle time range change (only for running summary)
  const handleTimeRangeChange = (newRange: string) => {
    setTimeRange(newRange);
  };

  // Handle close (Escape key or click outside)
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      document.body.style.overflow = 'hidden'; // Prevent background scrolling
    }

    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const getTitle = () => {
    switch (summaryType) {
      case 'running':
        return 'RUNNING SUMMARY';
      case 'online':
        return 'ONLINE SUMMARY';
      case 'offline':
        return 'OFFLINE SUMMARY';
    }
  };

  const getHeaders = () => {
    switch (summaryType) {
      case 'running':
        return ['MACHINE', 'RUN TIME', 'PERCENTAGE', 'LAST ACTIVE', 'PROGRAM'];
      case 'online':
        return ['MACHINE', 'ONLINE', 'HEALTH', 'SERVICES', 'LAST SEEN'];
      case 'offline':
        return ['MACHINE', 'OFFLINE', 'OFFLINE SINCE', 'SERVICE ERRORS', 'LAST STATUS'];
    }
  };

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
          <button className="retry-button" onClick={() => setTimeRange(timeRange)}>
            RETRY
          </button>
        </div>
      );
    }

    // Render based on summary type
    switch (summaryType) {
      case 'running':
        if (!runningData || runningData.machines.length === 0) {
          return <div className="summary-empty">No running data available</div>;
        }
        return runningData.machines.map((machine) => (
          <RunningSummaryRow key={machine.machine_id} machine={machine} />
        ));

      case 'online':
        if (!onlineData || onlineData.machines.length === 0) {
          return <div className="summary-empty">No machines online</div>;
        }
        return onlineData.machines.map((machine) => (
          <OnlineSummaryRow key={machine.machine_id} machine={machine} />
        ));

      case 'offline':
        if (!offlineData || offlineData.machines.length === 0) {
          return <div className="summary-empty">No machines offline</div>;
        }
        return offlineData.machines.map((machine) => (
          <OfflineSummaryRow key={machine.machine_id} machine={machine} />
        ));
    }
  };

  return (
    <div className="summary-modal-overlay" onClick={onClose}>
      <div className="summary-modal" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="summary-modal-header">
          <h2 className="summary-modal-title">{getTitle()}</h2>
          <button className="summary-modal-close" onClick={onClose}>
            ✕
          </button>
        </div>

        {/* Time Range Selector (only for running summary) */}
        {summaryType === 'running' && (
          <div className="summary-modal-controls">
            <TimeRangeSelector
              selectedRange={timeRange}
              onChange={handleTimeRangeChange}
              disabled={loading}
            />
          </div>
        )}

        {/* Column Headers */}
        {!loading && !error && (
          <div className="summary-headers">
            {getHeaders().map((header, index) => (
              <div key={index} className="summary-header">
                {header}
              </div>
            ))}
          </div>
        )}

        {/* Content Area */}
        <div className="summary-modal-content">
          {renderContent()}
        </div>
      </div>
    </div>
  );
};
