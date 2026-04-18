import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { useNavigate } from 'react-router-dom';
import { Select } from '../../components/ui';
import { API_BASE_URL } from '../../config/api';
import {
  clearStoredTabletCompressorId,
  readStoredTabletCompressorId,
  writeStoredTabletCompressorId,
} from './tabletCompressorStorage';
import { TABLET_DEFAULT_COMPRESSOR_PANE } from './tabletCompressorPaneConfig';
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

export type TabletSetupAssetKind = 'machine' | 'compressor';

interface TabletSetupPanelProps {
  /** CNC (`machine`) or Kaeser compressor (`compressor`) kiosk target */
  kind?: TabletSetupAssetKind;
  /** Called after a valid id is saved (default: navigate to tablet shell) */
  onSaved?: (id: number, kind: TabletSetupAssetKind) => void;
}

type AssetRow = { id: number; name: string };

export const TabletSetupPanel = ({ kind = 'machine', onSaved }: TabletSetupPanelProps) => {
  const navigate = useNavigate();
  const [value, setValue] = useState(() =>
    kind === 'machine'
      ? String(readStoredTabletMachineId() ?? '')
      : String(readStoredTabletCompressorId() ?? '')
  );
  const [error, setError] = useState<string | null>(null);
  const [assetRows, setAssetRows] = useState<AssetRow[]>([]);
  const [listHint, setListHint] = useState<string | null>(null);
  const [listLoad, setListLoad] = useState<'idle' | 'loading' | 'ready'>('idle');
  const [fetchError, setFetchError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const endpoint =
      kind === 'machine'
        ? `${API_BASE_URL}/api/machines?enabled_only=true&limit=500`
        : `${API_BASE_URL}/api/compressors?enabled_only=true&limit=500`;

    setListLoad('loading');
    setFetchError(null);
    setListHint(null);

    (async () => {
      try {
        const res = await fetch(endpoint);
        if (!res.ok) {
          const detail = await res.text();
          throw new Error(detail || `HTTP ${res.status}`);
        }
        const data: unknown = await res.json();
        if (cancelled) return;
        if (!Array.isArray(data)) {
          throw new Error('Unexpected response shape');
        }
        const rows: AssetRow[] = data
          .filter(
            (x): x is Record<string, unknown> =>
              Boolean(x) && typeof x === 'object' && 'id' in x && 'name' in x
          )
          .map((x) => ({
            id: Number(x.id),
            name: typeof x.name === 'string' ? x.name : String(x.name ?? ''),
          }))
          .filter((r) => Number.isFinite(r.id) && r.id > 0 && r.name.length > 0)
          .sort((a, b) => a.name.localeCompare(b.name, undefined, { sensitivity: 'base' }));

        setAssetRows(rows);
        setListLoad('ready');

        const stored =
          kind === 'machine' ? readStoredTabletMachineId() : readStoredTabletCompressorId();
        if (stored != null && rows.some((r) => r.id === stored)) {
          setValue(String(stored));
        } else if (stored != null && rows.length > 0) {
          setValue('');
          setListHint(
            `Stored kiosk ID (${stored}) is disabled or missing from the fleet list. Pick an enabled asset below.`
          );
        }
      } catch (e) {
        if (!cancelled) {
          setAssetRows([]);
          setListLoad('ready');
          setFetchError(e instanceof Error ? e.message : 'Could not load asset list.');
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [kind]);

  const showDropdown = assetRows.length > 0;
  const showManualEmpty =
    listLoad === 'ready' && assetRows.length === 0 && fetchError === null;
  const showManualFallback = fetchError !== null;

  const assetSelectOptions = useMemo(
    () => [
      {
        value: '',
        label:
          kind === 'machine' ? '— Select a machine —' : '— Select a compressor —',
      },
      ...assetRows.map((row) => ({
        value: String(row.id),
        label: `${row.name} (ID ${row.id})`,
      })),
    ],
    [kind, assetRows]
  );

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    const id = parsePositiveInt(value);
    if (id === null) {
      setError(
        kind === 'machine'
          ? showDropdown
            ? 'Choose a machine from the list.'
            : 'Enter a positive numeric machine ID (see dashboard CNC edit form).'
          : showDropdown
            ? 'Choose a compressor from the list.'
            : 'Enter a positive numeric compressor ID (see dashboard compressor edit form).'
      );
      return;
    }
    setError(null);
    if (kind === 'machine') {
      writeStoredTabletMachineId(id);
    } else {
      writeStoredTabletCompressorId(id);
    }
    if (onSaved) {
      onSaved(id, kind);
    } else if (kind === 'machine') {
      navigate(`/tablet/${id}/${TABLET_DEFAULT_PANE}`, { replace: true });
    } else {
      navigate(`/tablet/compressor/${id}/${TABLET_DEFAULT_COMPRESSOR_PANE}`, { replace: true });
    }
  };

  const handleClear = () => {
    if (kind === 'machine') {
      clearStoredTabletMachineId();
    } else {
      clearStoredTabletCompressorId();
    }
    setValue('');
    setError(null);
    setListHint(null);
  };

  const selectId = kind === 'machine' ? 'tablet-machine-select' : 'tablet-compressor-select';
  const manualId =
    kind === 'machine' ? 'tablet-machine-id-manual' : 'tablet-compressor-id-manual';

  return (
    <div className="tablet-setup-panel">
      <p className="tablet-setup-intro">
        {kind === 'machine'
          ? 'CNC kiosk: choose an enabled machine once per browser (multi-tablet builds share one deploy).'
          : 'Compressor kiosk: choose an enabled compressor once per browser.'}
      </p>
      <form className="tablet-setup-form" onSubmit={handleSubmit}>
        {listLoad === 'loading' && (
          <p className="tablet-setup-list-hint" aria-live="polite">
            Loading fleet list…
          </p>
        )}
        {listHint && (
          <p className="tablet-setup-list-hint" role="status">
            {listHint}
          </p>
        )}
        {showDropdown && (
          <>
            <label className="tablet-setup-label" htmlFor={selectId}>
              {kind === 'machine' ? 'ENABLED MACHINES' : 'ENABLED COMPRESSORS'}
            </label>
            <Select
              id={selectId}
              className="tablet-setup-custom-select"
              value={value}
              onChange={(next) => {
                setValue(next);
                setError(null);
              }}
              options={assetSelectOptions}
              disabled={listLoad !== 'ready'}
            />
          </>
        )}
        {showManualFallback && (
          <>
            <p className="tablet-setup-list-hint text-error" role="alert">
              {fetchError} Enter an ID manually below.
            </p>
            <label className="tablet-setup-label" htmlFor={`${manualId}-fallback`}>
              {kind === 'machine' ? 'MACHINE ID (manual)' : 'COMPRESSOR ID (manual)'}
            </label>
            <input
              id={`${manualId}-fallback`}
              type="number"
              min={1}
              step={1}
              className="tablet-setup-input"
              value={value}
              onChange={(e) => setValue(e.target.value)}
              placeholder={kind === 'machine' ? 'e.g. 3' : 'e.g. 1'}
              autoComplete="off"
            />
          </>
        )}
        {showManualEmpty && (
          <>
            <p className="tablet-setup-list-hint">
              {kind === 'machine'
                ? 'No enabled CNC machines returned. Enable one on the fleet dashboard, or enter an ID manually.'
                : 'No enabled compressors returned. Enable one on the fleet dashboard, or enter an ID manually.'}
            </p>
            <label className="tablet-setup-label" htmlFor={manualId}>
              {kind === 'machine' ? 'MACHINE ID' : 'COMPRESSOR ID'}
            </label>
            <input
              id={manualId}
              type="number"
              min={1}
              step={1}
              className="tablet-setup-input"
              value={value}
              onChange={(e) => setValue(e.target.value)}
              placeholder={kind === 'machine' ? 'e.g. 3' : 'e.g. 1'}
              autoComplete="off"
            />
          </>
        )}
        {error && <div className="tablet-setup-error text-error">{error}</div>}
        <div className="tablet-setup-actions">
          <button
            type="submit"
            className="tablet-setup-btn primary"
            disabled={listLoad === 'loading'}
          >
            {kind === 'machine' ? '[ OPEN CNC TABLET ]' : '[ OPEN COMPRESSOR TABLET ]'}
          </button>
          <button type="button" className="tablet-setup-btn" onClick={handleClear}>
            [ CLEAR STORED ID ]
          </button>
        </div>
      </form>
    </div>
  );
};
