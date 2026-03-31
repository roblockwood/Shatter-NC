import React from 'react';
import type { ChartTimeAxisMode } from '../../utils/chartTimeAxis';
import './ChartTimeAxisToggle.css';

export type ChartTimeAxisToggleProps = {
  timeAxisMode: ChartTimeAxisMode;
  toggleTimeAxisMode: () => void;
  className?: string;
};

/** Switches this chart only between relative and clock axis labels (parent owns state). */
export const ChartTimeAxisToggle: React.FC<ChartTimeAxisToggleProps> = ({
  timeAxisMode,
  toggleTimeAxisMode,
  className = '',
}) => {
  return (
    <button
      type="button"
      className={`chart-time-axis-toggle ${className}`.trim()}
      onClick={(e) => {
        e.stopPropagation();
        toggleTimeAxisMode();
      }}
      title={
        timeAxisMode === 'relative'
          ? 'Switch to clock time on this chart'
          : 'Switch to relative time on this chart (e.g. 45m, 3h)'
      }
    >
      {timeAxisMode === 'relative' ? '[CLK]' : '[REL]'}
    </button>
  );
};
