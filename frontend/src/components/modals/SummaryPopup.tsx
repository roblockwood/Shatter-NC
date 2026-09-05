import React, { useState, useEffect, useRef } from 'react';
import { summaryApi } from '../../api/summary';
import type { RunningSummary, MachinesSummary } from '../../api/summary';
import { RunningSummaryRow } from './summary/RunningSummaryRow';
import { MachineStatusRow } from './summary/MachineStatusRow';
import './SummaryPopup.css';

interface SummaryPopupProps {
  summaryType: 'running' | 'machines';
  anchorRef: React.RefObject<HTMLElement | null>;
  onClose: () => void;
  onMouseEnter?: () => void;
  onMouseLeave?: () => void;
  onMachineClick?: (machineId: number) => void;
  onAssetClick?: (asset: { kind: 'cnc' | 'compressor'; id: number }) => void;
}

export const SummaryPopup: React.FC<SummaryPopupProps> = ({
  summaryType,
  anchorRef,
  onClose,
  onMouseEnter,
  onMouseLeave,
  onMachineClick,
  onAssetClick,
}) => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [runningData, setRunningData] = useState<RunningSummary | null>(null);
  const [machinesData, setMachinesData] = useState<MachinesSummary | null>(null);
  const [timeRange, setTimeRange] = useState<'1h' | '8h' | '24h' | '7d'>('8h');
  const [runningTimeRange, setRunningTimeRange] = useState<'1h' | '8h' | '24h' | '7d'>('24h');
  const popupRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const fetchData = async (isInitial: boolean = false) => {
      if (isInitial) {
        setLoading(true);
      }
      setError(null);

      try {
        if (summaryType === 'running') {
          const runningResponse = await summaryApi.getRunning(runningTimeRange);
          setRunningData(runningResponse);
        } else {
          const machinesResponse = await summaryApi.getMachines(timeRange);
          setMachinesData(machinesResponse);
        }
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
  }, [summaryType, timeRange, runningTimeRange]);

  useEffect(() => {
    if (!anchorRef.current || !popupRef.current) return;
    const anchorRect = anchorRef.current.getBoundingClientRect();
    const popup = popupRef.current;
    popup.style.top = `${anchorRect.bottom + 8}px`;
    popup.style.left = `${anchorRect.left}px`;
  }, [anchorRef, loading]);

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
    if (summaryType === 'running') {
      return 'RUNNING MACHINES (24H)';
    }
    if (machinesData) {
      return `MACHINE STATUS (${machinesData.online_count}/${machinesData.total_machines} ONLINE)`;
    }
    return 'MACHINE STATUS';
  };

  const getHeaders = () => {
    if (summaryType === 'running') {
      return ['MACHINE', 'RUN TIME', 'PERCENTAGE', 'POLLING'];
    }
    return ['', 'DURATION', 'UPTIME', 'POLLING'];
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

    if (summaryType === 'running') {
      if (!runningData || runningData.machines.length === 0) {
        return <div className="summary-popup-empty">No running data (24h)</div>;
      }
      return runningData.machines.slice(0, 10).map((machine) => (
        <RunningSummaryRow
          key={machine.machine_id}
          machine={machine}
          compact={true}
          timeRange={runningTimeRange}
          onMachineClick={onMachineClick}
        />
      ));
    }

    if (!machinesData || machinesData.machines.length === 0) {
      return <div className="summary-popup-empty">No machines</div>;
    }
    return machinesData.machines.map((machine) => (
      <MachineStatusRow
        key={`${machine.asset_kind ?? 'cnc'}-${machine.machine_id}`}
        machine={machine}
        compact={true}
        timeRange={timeRange}
        onMachineClick={onMachineClick}
        onAssetClick={onAssetClick}
      />
    ));
  };

  const activeRange = summaryType === 'machines' ? timeRange : runningTimeRange;

  return (
    <div
      ref={popupRef}
      className="summary-popup"
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
    >
      <div className="summary-popup-header">
        <h3 className="summary-popup-title">{getTitle()}</h3>
        {!loading && !error && (
          <div className="summary-popup-header-controls">
            {(['1h', '8h', '24h', '7d'] as const).map((range) => (
              <button
                key={range}
                className={`time-range-btn ${activeRange === range ? 'active' : ''}`}
                onClick={() => {
                  if (summaryType === 'machines') {
                    setTimeRange(range);
                  } else {
                    setRunningTimeRange(range);
                  }
                }}
                disabled={loading}
              >
                [{range.toUpperCase()}]
              </button>
            ))}
          </div>
        )}
        <button className="summary-popup-close" onClick={onClose}>
          ✕
        </button>
      </div>

      {!loading && !error && (
        <div className="summary-popup-headers">
          {getHeaders().map((header, index) => (
            <div key={index} className="summary-popup-header-cell">
              {header}
            </div>
          ))}
        </div>
      )}

      <div className="summary-popup-content">{renderContent()}</div>
    </div>
  );
};
