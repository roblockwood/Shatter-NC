import { useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  clearStoredTabletMachineId,
  readStoredTabletMachineId,
  writeStoredTabletMachineId,
} from './tabletMachineStorage';
import { TABLET_DEFAULT_PANE } from './tabletPaneConfig';
import './tablet.css';

function parsePositiveInt(raw: string): number | null {
  const n = Number.parseInt(raw.trim(), 10);
  if (!Number.isFinite(n) || n <= 0) {
    return null;
  }
  return n;
}

interface TabletSetupPanelProps {
  /** Called after a valid id is saved (default: navigate to tablet shell) */
  onSaved?: (machineId: number) => void;
}

export const TabletSetupPanel = ({ onSaved }: TabletSetupPanelProps) => {
  const navigate = useNavigate();
  const [value, setValue] = useState(() => String(readStoredTabletMachineId() ?? ''));
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const id = parsePositiveInt(value);
    if (id === null) {
      setError('Enter a positive numeric machine ID (see dashboard edit form).');
      return;
    }
    setError(null);
    writeStoredTabletMachineId(id);
    if (onSaved) {
      onSaved(id);
    } else {
      navigate(`/tablet/${id}/${TABLET_DEFAULT_PANE}`, { replace: true });
    }
  };

  const handleClear = () => {
    clearStoredTabletMachineId();
    setValue('');
    setError(null);
  };

  return (
    <div className="tablet-setup-panel">
      <p className="tablet-setup-intro">
        One build serves every tablet: set the CNC machine ID on each device once. This browser only —
        other tablets keep their own IDs.
      </p>
      <form className="tablet-setup-form" onSubmit={handleSubmit}>
        <label className="tablet-setup-label" htmlFor="tablet-machine-id">
          MACHINE ID
        </label>
        <input
          id="tablet-machine-id"
          type="number"
          min={1}
          step={1}
          className="tablet-setup-input"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="e.g. 3"
          autoComplete="off"
        />
        {error && <div className="tablet-setup-error text-error">{error}</div>}
        <div className="tablet-setup-actions">
          <button type="submit" className="tablet-setup-btn primary">
            [ OPEN TABLET ]
          </button>
          <button type="button" className="tablet-setup-btn" onClick={handleClear}>
            [ CLEAR STORED ID ]
          </button>
        </div>
      </form>
    </div>
  );
};
