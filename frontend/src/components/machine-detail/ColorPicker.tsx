import React from 'react';
import { createPortal } from 'react-dom';
import './ColorPicker.css';

interface ColorOption {
  value: number;
  name: string;
  hex: string;
}

const COLOR_OPTIONS: ColorOption[] = [
  { value: 0, name: 'NONE', hex: '#666666' },
  { value: 1, name: 'BLUE', hex: '#0066ff' },
  { value: 2, name: 'RED', hex: '#ff0000' },
  { value: 3, name: 'PURPLE', hex: '#9900ff' },
  { value: 4, name: 'GREEN', hex: '#00ff00' },
  { value: 5, name: 'LT BLUE', hex: '#00ccff' },
  { value: 6, name: 'YELLOW', hex: '#ffff00' },
  { value: 7, name: 'WHITE', hex: '#ffffff' },
];

interface ColorPickerProps {
  currentColor: number;
  onColorSelect: (color: number) => void;
  onClose: () => void;
  position?: { top: number; left: number };
}

export const ColorPicker: React.FC<ColorPickerProps> = ({
  currentColor,
  onColorSelect,
  onClose,
  position,
}) => {
  const handleColorClick = (color: number) => {
    onColorSelect(color);
    onClose();
  };

  const pickerContent = (
    <>
      {/* Backdrop to close picker */}
      <div className="color-picker-backdrop" onClick={onClose} />
      
      {/* Color picker palette */}
      <div
        className="color-picker-palette"
        style={position ? { top: `${position.top}px`, left: `${position.left}px` } : undefined}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="color-picker-header">
          <span className="color-picker-title">Select Color</span>
          <button className="color-picker-close" onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>
        <div className="color-picker-grid">
          {COLOR_OPTIONS.map((color) => (
            <button
              key={color.value}
              className={`color-picker-swatch ${
                currentColor === color.value ? 'color-picker-swatch-selected' : ''
              }`}
              onClick={() => handleColorClick(color.value)}
              title={color.name}
              aria-label={color.name}
            >
              <span
                className="color-picker-swatch-color"
                style={{ backgroundColor: color.hex }}
              />
              <span className="color-picker-swatch-name">{color.name}</span>
            </button>
          ))}
        </div>
      </div>
    </>
  );

  // Render using portal to escape overflow constraints
  return createPortal(pickerContent, document.body);
};

