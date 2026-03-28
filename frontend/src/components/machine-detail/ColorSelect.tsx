import React, { useState, useRef, useEffect } from 'react';
import './ColorSelect.css';

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

interface ColorSelectProps {
  value: number;
  onChange: (value: number) => void;
  disabled?: boolean;
  /** Same look as interactive mode, but no dropdown (e.g. tool table view). */
  readOnly?: boolean;
  className?: string;
}

export const ColorSelect: React.FC<ColorSelectProps> = ({
  value,
  onChange,
  disabled = false,
  readOnly = false,
  className = '',
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const selectRef = useRef<HTMLDivElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  const selectedColor = COLOR_OPTIONS.find(opt => opt.value === value) || COLOR_OPTIONS[0];

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        selectRef.current &&
        !selectRef.current.contains(event.target as Node) &&
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [isOpen]);

  useEffect(() => {
    if (isOpen && dropdownRef.current && selectRef.current) {
      const rect = selectRef.current.getBoundingClientRect();
      const dropdown = dropdownRef.current;
      const viewportHeight = window.innerHeight;
      const dropdownHeight = dropdown.offsetHeight;

      // Position dropdown below or above based on available space
      const spaceBelow = viewportHeight - rect.bottom;
      const spaceAbove = rect.top;

      if (spaceBelow < dropdownHeight && spaceAbove > spaceBelow) {
        dropdown.style.bottom = '100%';
        dropdown.style.top = 'auto';
        dropdown.style.marginBottom = '4px';
        dropdown.style.marginTop = '0';
      } else {
        dropdown.style.top = '100%';
        dropdown.style.bottom = 'auto';
        dropdown.style.marginTop = '4px';
        dropdown.style.marginBottom = '0';
      }
    }
  }, [isOpen]);

  const handleToggle = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!disabled && !readOnly) {
      setIsOpen(!isOpen);
    }
  };

  const handleSelect = (colorValue: number) => {
    if (!disabled && !readOnly && colorValue !== value) {
      onChange(colorValue);
    }
    setIsOpen(false);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (disabled || readOnly) return;
    e.stopPropagation();

    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleToggle(e as any);
    } else if (e.key === 'Escape') {
      setIsOpen(false);
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      if (!isOpen) {
        setIsOpen(true);
      } else {
        const currentIndex = COLOR_OPTIONS.findIndex(opt => opt.value === value);
        const nextIndex = (currentIndex + 1) % COLOR_OPTIONS.length;
        handleSelect(COLOR_OPTIONS[nextIndex].value);
      }
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      if (isOpen) {
        const currentIndex = COLOR_OPTIONS.findIndex(opt => opt.value === value);
        const prevIndex = currentIndex <= 0 ? COLOR_OPTIONS.length - 1 : currentIndex - 1;
        handleSelect(COLOR_OPTIONS[prevIndex].value);
      }
    }
  };

  return (
    <div className={`color-select-wrapper ${className}`}>
      <div
        ref={selectRef}
        className={`color-select ${isOpen ? 'open' : ''} ${disabled ? 'disabled' : ''} ${readOnly ? 'read-only' : ''}`}
        onClick={handleToggle}
        onKeyDown={handleKeyDown}
        onMouseDown={(e) => e.stopPropagation()}
        tabIndex={disabled || readOnly ? -1 : 0}
        role={readOnly ? undefined : 'combobox'}
        aria-expanded={readOnly ? undefined : isOpen}
        aria-haspopup={readOnly ? undefined : 'listbox'}
        aria-disabled={disabled || readOnly}
      >
        <span className="color-select-indicator" style={{ backgroundColor: selectedColor.hex }} />
        <span className="color-select-value">{selectedColor.name}</span>
        <span
          className={`color-select-arrow ${readOnly ? 'color-select-arrow-placeholder' : ''}`}
          aria-hidden
        >
          ▼
        </span>
      </div>
      {isOpen && !readOnly && (
        <div
          ref={dropdownRef}
          className="color-select-dropdown"
          role="listbox"
          onClick={(e) => e.stopPropagation()}
          onMouseDown={(e) => e.stopPropagation()}
        >
          {COLOR_OPTIONS.map((color) => (
            <div
              key={color.value}
              className={`color-select-option ${color.value === value ? 'selected' : ''}`}
              onClick={() => handleSelect(color.value)}
              onMouseDown={(e) => e.stopPropagation()}
              role="option"
              aria-selected={color.value === value}
            >
              <span className="color-select-option-indicator" style={{ backgroundColor: color.hex }} />
              {color.value === value && <span className="color-select-checkmark">✓</span>}
              <span className="color-select-option-label">{color.name}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

