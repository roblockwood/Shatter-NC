import React from 'react';
import './TerminalBox.css';

interface TerminalBoxProps {
  children: React.ReactNode;
  title?: string;
  className?: string;
  variant?: 'single' | 'double' | 'rounded';
  glow?: boolean;
}

export const TerminalBox: React.FC<TerminalBoxProps> = ({
  children,
  title,
  className = '',
  variant = 'single',
  glow = false,
}) => {
  const borders = {
    single: {
      topLeft: '┌',
      topRight: '┐',
      bottomLeft: '└',
      bottomRight: '┘',
      horizontal: '─',
      vertical: '│',
      divider: '├─┤',
    },
    double: {
      topLeft: '╔',
      topRight: '╗',
      bottomLeft: '╚',
      bottomRight: '╝',
      horizontal: '═',
      vertical: '║',
      divider: '╠═╣',
    },
    rounded: {
      topLeft: '╭',
      topRight: '╮',
      bottomLeft: '╰',
      bottomRight: '╯',
      horizontal: '─',
      vertical: '│',
      divider: '├─┤',
    },
  };

  const b = borders[variant];

  return (
    <div className={`terminal-box ${glow ? 'terminal-box-glow' : ''} ${className}`}>
      {title ? (
        <>
          <div className="terminal-box-header">
            {b.topLeft} {title} {b.horizontal.repeat(Math.max(0, 50 - title.length))} {b.topRight}
          </div>
          <div className="terminal-box-content">
            {children}
          </div>
          <div className="terminal-box-footer">
            {b.bottomLeft}{b.horizontal.repeat(52)}{b.bottomRight}
          </div>
        </>
      ) : (
        <>
          <div className="terminal-box-header">
            {b.topLeft}{b.horizontal.repeat(54)}{b.topRight}
          </div>
          <div className="terminal-box-content">
            {children}
          </div>
          <div className="terminal-box-footer">
            {b.bottomLeft}{b.horizontal.repeat(54)}{b.bottomRight}
          </div>
        </>
      )}
    </div>
  );
};
