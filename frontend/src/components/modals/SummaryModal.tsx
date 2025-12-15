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
  
  // Use different default time ranges for different summary types
  const getDefaultTimeRange = () => {
    switch (summaryType) {
      case 'running':
        return '24h';
      case 'online':
        return '8h';
      default:
        return '24h';
    }
  };
  
  const [currentTimeRange, setCurrentTimeRange] = useState(getDefaultTimeRange());

  // Fetch data based on summary type
  useEffect(() => {
    if (!isOpen) return;

    const fetchData = async (isInitial: boolean = false) => {
      if (isInitial) {
        setLoading(true);
      }
      setError(null);

      try {
        switch (summaryType) {
          case 'running':
            const runningResponse = await summaryApi.getRunning(timeRange);
            setRunningData(runningResponse);
            break;
          case 'online':
            const onlineResponse = await summaryApi.getOnline(currentTimeRange);
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
        if (isInitial) {
          setLoading(false);
        }
      }
    };

    // Fetch immediately
    fetchData(true);

    // Set up polling to refresh data every 2 seconds (without showing loading state)
    const pollInterval = setInterval(() => fetchData(false), 2000);

    return () => clearInterval(pollInterval);
  }, [isOpen, summaryType, timeRange, currentTimeRange]);

  // Handle time range change
  const handleTimeRangeChange = (newRange: string) => {
    if (summaryType === 'running') {
      setTimeRange(newRange);
    } else if (summaryType === 'online') {
      setCurrentTimeRange(newRange);
    }
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
        return `RUNNING MACHINES (${timeRange.toUpperCase()})`;
      case 'online':
        return 'ONLINE SUMMARY';
      case 'offline':
        return 'OFFLINE SUMMARY';
    }
  };

  const getHeaders = () => {
    switch (summaryType) {
      case 'running':
        return ['MACHINE', 'RUN TIME', 'PERCENTAGE', 'POLLING'];
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
          <RunningSummaryRow 
            key={machine.machine_id} 
            machine={machine} 
            compact={false}
            timeRange={timeRange as '1h' | '8h' | '24h' | '7d'}
          />
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
      <div className={`summary-modal summary-modal-${summaryType}`} onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="summary-modal-header">
          <h2 className="summary-modal-title">{getTitle()}</h2>
          {summaryType === 'running' && !loading && !error && (
            <div className="summary-modal-header-controls">
              <button
                className={`time-range-btn ${timeRange === '1h' ? 'active' : ''}`}
                onClick={() => handleTimeRangeChange('1h')}
                disabled={loading}
              >
                [1H]
              </button>
              <button
                className={`time-range-btn ${timeRange === '8h' ? 'active' : ''}`}
                onClick={() => handleTimeRangeChange('8h')}
                disabled={loading}
              >
                [8H]
              </button>
              <button
                className={`time-range-btn ${timeRange === '24h' ? 'active' : ''}`}
                onClick={() => handleTimeRangeChange('24h')}
                disabled={loading}
              >
                [24H]
              </button>
              <button
                className={`time-range-btn ${timeRange === '7d' ? 'active' : ''}`}
                onClick={() => handleTimeRangeChange('7d')}
                disabled={loading}
              >
                [7D]
              </button>
            </div>
          )}
          {summaryType === 'online' && (
            <div className="summary-modal-header-controls">
              <TimeRangeSelector
                selectedRange={currentTimeRange}
                onChange={handleTimeRangeChange}
                disabled={loading}
              />
            </div>
          )}
          <button className="summary-modal-close" onClick={onClose}>
            ✕
          </button>
        </div>

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
