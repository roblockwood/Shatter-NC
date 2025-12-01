import React from 'react';
import './ProgressBar.css';

interface ProgressBarProps {
  value: number; // 0-100
  width?: number; // number of characters
  showPercentage?: boolean;
  variant?: 'blocks' | 'shaded';
  className?: string;
}

export const ProgressBar: React.FC<ProgressBarProps> = ({
  value,
  width = 20,
  showPercentage = true,
  variant = 'blocks',
  className = '',
}) => {
  // Clamp value between 0 and 100
  const clampedValue = Math.max(0, Math.min(100, value));
  const fillWidth = Math.round((clampedValue / 100) * width);

  const chars = {
    blocks: {
      full: '█',
      empty: '░',
      partial: '▌',
    },
    shaded: {
      full: '█',
      empty: '─',
      partial: '▌',
    },
  };

  const { full, empty, partial } = chars[variant];

  // Build the progress bar
  let bar = '';

  for (let i = 0; i < width; i++) {
    if (i < fillWidth) {
      bar += full;
    } else if (i === fillWidth && clampedValue % (100 / width) > 0) {
      bar += partial;
    } else {
      bar += empty;
    }
  }

  return (
    <span className={`progress-bar ${className}`}>
      {bar}
      {showPercentage && ` ${Math.round(clampedValue)}%`}
    </span>
  );
};
