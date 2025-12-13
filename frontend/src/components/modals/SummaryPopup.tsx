import React, { useState, useEffect, useRef } from 'react';
import { summaryApi } from '../../api/summary';
import type {
  OnlineSummary,
  OfflineSummary,
  RunningSummary,
  MachinesSummary,
} from '../../api/summary';
import { OnlineSummaryRow } from './summary/OnlineSummaryRow';
import { OfflineSummaryRow } from './summary/OfflineSummaryRow';
import { RunningSummaryRow } from './summary/RunningSummaryRow';
import { MachineStatusRow } from './summary/MachineStatusRow';
import './SummaryPopup.css';

interface SummaryPopupProps {
  summaryType: 'online' | 'offline' | 'running' | 'machines';
  anchorRef: React.RefObject<HTMLElement | null>;
  onClose: () => void;
  onMouseEnter?: () => void;
  onMouseLeave?: () => void;
}

export const SummaryPopup: React.FC<SummaryPopupProps> = ({
  summaryType,
  anchorRef,
  onClose,
  onMouseEnter,
  onMouseLeave,
}) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [onlineData, setOnlineData] = useState<OnlineSummary | null>(null);
  const [offlineData, setOfflineData] = useState<OfflineSummary | null>(null);
  const [runningData, setRunningData] = useState<RunningSummary | null>(null);
  const [machinesData, setMachinesData] = useState<MachinesSummary | null>(null);
  const popupRef = useRef<HTMLDivElement>(null);

  // Fetch data based on summary type
  useEffect(() => {
    const fetchData = async (isInitial: boolean = false) => {
      if (isInitial) {
        setLoading(true);
      }
      setError(null);

      try {
        switch (summaryType) {
          case 'online':
            const onlineResponse = await summaryApi.getOnline();
            setOnlineData(onlineResponse);
            break;
          case 'offline':
            const offlineResponse = await summaryApi.getOffline();
            setOfflineData(offlineResponse);
            break;
          case 'running':
            const runningResponse = await summaryApi.getRunning('24h');
            setRunningData(runningResponse);
            break;
          case 'machines':
            const machinesResponse = await summaryApi.getMachines();
            setMachinesData(machinesResponse);
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
  }, [summaryType]);

  // Position popup near anchor element
  useEffect(() => {
    if (!anchorRef.current || !popupRef.current) return;

    const anchorRect = anchorRef.current.getBoundingClientRect();
    const popup = popupRef.current;

    // Position below the anchor with a small offset
    popup.style.top = `${anchorRect.bottom + 8}px`;
    popup.style.left = `${anchorRect.left}px`;
  }, [anchorRef, loading]);

  // Close on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        popupRef.current &&
        !popupRef.current.contains(e.target as Node) &&
        anchorRef.current &&
        !anchorRef.current.contains(e.target as Node)
      ) {
        onClose();
      }
    };

    // Close on Escape key
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleEscape);

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [anchorRef, onClose]);

  const getTitle = () => {
    switch (summaryType) {
      case 'online':
        return 'ONLINE MACHINES';
      case 'offline':
        return 'OFFLINE MACHINES';
      case 'running':
        return 'RUNNING MACHINES (24H)';
      case 'machines':
        if (machinesData) {
          return `MACHINE STATUS (${machinesData.online_count}/${machinesData.total_machines} ONLINE)`;
        }
        return 'MACHINE STATUS';
    }
  };

  const getHeaders = () => {
    switch (summaryType) {
      case 'online':
        return ['MACHINE', 'ONLINE', 'HEALTH', 'SERVICES'];
      case 'offline':
        return ['MACHINE', 'OFFLINE', 'SINCE', 'SERVICES'];
      case 'running':
        return ['MACHINE', 'RUN TIME', 'PERCENTAGE', 'LAST ACTIVE'];
      case 'machines':
        return ['', 'DURATION', 'POLLING (1H)', 'UPTIME (8H)'];
    }
  };

  const renderContent = () => {
    if (loading) {
      return (
        <div className="summary-popup-loading">
          <div className="loading-text">LOADING<span className="loading-dots">...</span></div>
        </div>
      );
    }

    if (error) {
      return (
        <div className="summary-popup-error">
          <div className="error-message">ERROR: {error}</div>
        </div>
      );
    }

    // Render based on summary type
    switch (summaryType) {
      case 'online':
        if (!onlineData || onlineData.machines.length === 0) {
          return <div className="summary-popup-empty">No machines online</div>;
        }
        return onlineData.machines.slice(0, 10).map((machine) => (
          <OnlineSummaryRow key={machine.machine_id} machine={machine} compact={true} />
        ));

      case 'offline':
        if (!offlineData || offlineData.machines.length === 0) {
          return <div className="summary-popup-empty">No machines offline</div>;
        }
        return offlineData.machines.slice(0, 10).map((machine) => (
          <OfflineSummaryRow key={machine.machine_id} machine={machine} compact={true} />
        ));

      case 'running':
        if (!runningData || runningData.machines.length === 0) {
          return <div className="summary-popup-empty">No running data (24h)</div>;
        }
        return runningData.machines.slice(0, 10).map((machine) => (
          <RunningSummaryRow key={machine.machine_id} machine={machine} compact={true} />
        ));

      case 'machines':
        if (!machinesData || machinesData.machines.length === 0) {
          return <div className="summary-popup-empty">No machines</div>;
        }
        return machinesData.machines.map((machine) => (
          <MachineStatusRow key={machine.machine_id} machine={machine} compact={true} />
        ));
    }
  };

  return (
    <div
      ref={popupRef}
      className="summary-popup"
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
    >
      {/* Header */}
      <div className="summary-popup-header">
        <h3 className="summary-popup-title">{getTitle()}</h3>
        <button className="summary-popup-close" onClick={onClose}>
          ✕
        </button>
      </div>

      {/* Column Headers */}
      {!loading && !error && (
        <div className="summary-popup-headers">
          {getHeaders().map((header, index) => (
            <div key={index} className="summary-popup-header-cell">
              {header}
            </div>
          ))}
        </div>
      )}

      {/* Content Area */}
      <div className="summary-popup-content">
        {renderContent()}
      </div>
    </div>
  );
};
