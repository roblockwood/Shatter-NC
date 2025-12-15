import React from 'react';
import './TimeRangeSelector.css';

interface TimeRangeSelectorProps {
  selectedRange: string;
  onChange: (range: string) => void;
  disabled?: boolean;
}

const TIME_RANGES = [
  { value: '1h', label: '1H' },
  { value: '8h', label: '8H' },
  { value: '24h', label: '24H' },
  { value: '7d', label: '7D' },
];

export const TimeRangeSelector: React.FC<TimeRangeSelectorProps> = ({
  selectedRange,
  onChange,
  disabled = false,
}) => {
  return (
    <div className="time-range-selector">
      <span className="time-range-label">TIME RANGE:</span>
      {TIME_RANGES.map((range) => (
        <button
          key={range.value}
          className={`time-range-option ${selectedRange === range.value ? 'selected' : ''}`}
          onClick={() => onChange(range.value)}
          disabled={disabled}
        >
          {range.label}
        </button>
      ))}
    </div>
  );
};
