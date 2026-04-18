import React from 'react';
import type { LatestProductionRunRow } from '../../hooks/useLatestMachineProductionRun';

interface ProductionRunCompactSummaryProps {
  latestRun: LatestProductionRunRow | null;
  latestRunLoading: boolean;
  partDisplayMode: 'cycle' | 'parts';
}

export const ProductionRunCompactSummary: React.FC<ProductionRunCompactSummaryProps> = ({
  latestRun,
  latestRunLoading,
  partDisplayMode,
}) => (
  <>
    {latestRunLoading && !latestRun && 'LOADING...'}
    {!latestRunLoading && !latestRun && 'NO RECENT RUNS'}
    {latestRun && (
      <>
        <span className="production-run-meta">
          {latestRun.program_no || 'UNKNOWN'} ·{' '}
          {partDisplayMode === 'cycle' ? `cycles: ${latestRun.cycles}` : `parts: ${latestRun.part_count}`}
        </span>
        <ProductionRunUtilMini latestRun={latestRun} />
      </>
    )}
  </>
);

function ProductionRunUtilMini({ latestRun }: { latestRun: LatestProductionRunRow }) {
  const runStartMs = new Date(latestRun.run_start).getTime();
  const runEndMs = new Date(latestRun.run_end).getTime();
  const totalMs = Math.max(1, runEndMs - runStartMs);
  let activeMs = 0;
  for (const seg of latestRun.segments || []) {
    if ((seg.status || '').toLowerCase() !== 'operating') continue;
    const s0 = new Date(seg.start_time).getTime();
    const s1 = new Date(seg.end_time).getTime();
    if (!isNaN(s0) && !isNaN(s1) && s1 >= s0) activeMs += s1 - s0;
  }
  const utilPct = Math.min(100, Math.max(0, Math.round((activeMs / totalMs) * 100)));
  const runStartMs2 = new Date(latestRun.run_start).getTime();
  const runEndMs2 = new Date(latestRun.run_end).getTime();
  const span = Math.max(1, runEndMs2 - runStartMs2);
  return (
    <span className="production-run-util-row">
      <span className="production-run-util text-dim" title="Operating time / total run time">
        util: {utilPct}%
      </span>
      <span className="production-run-bar-track">
        {(latestRun.segments || []).map((seg, idx) => {
          const sStartMs = new Date(seg.start_time).getTime();
          const sEndMs = new Date(seg.end_time).getTime();
          const left = ((sStartMs - runStartMs2) / span) * 100;
          const width = Math.max(2, ((sEndMs - sStartMs) / span) * 100);
          const status = (seg.status || '').toLowerCase();
          const statusClass =
            status === 'operating'
              ? 'mini-segment-operating'
              : status === 'standby'
              ? 'mini-segment-standby'
              : status === 'stopped'
              ? 'mini-segment-stopped'
              : status === 'error'
              ? 'mini-segment-error'
              : status === 'off'
              ? 'mini-segment-off'
              : 'mini-segment-standby';
          return (
            <span
              key={idx}
              className={`production-run-segment ${statusClass}`}
              style={{ left: `${left}%`, width: `${width}%` }}
            />
          );
        })}
      </span>
    </span>
  );
}
