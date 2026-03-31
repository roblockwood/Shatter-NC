import React from 'react';
import { PollingStatusLight } from '../ui/PollingStatusLight';
import type { CompressorStatus } from '../../hooks/useWebSocket';
import { asciiFooterLine, asciiHeaderLeft } from '../../utils/terminalFrame';
import './AlarmPane.css';

interface CompressorOverviewPaneProps {
  compressor: CompressorStatus;
}

function safeJsonStringify(value: unknown): string {
  try {
    return JSON.stringify(value, null, 2) ?? 'null';
  } catch {
    return String(value);
  }
}

function statusBracket(status: string, online: boolean): string {
  if (!online) return `[OFFLINE]`;
  const s = (status || 'unknown').toUpperCase().replace(/\s+/g, '_');
  const short = s.length > 14 ? s.slice(0, 14) : s;
  return `[${short}]`;
}

export const CompressorOverviewPane: React.FC<CompressorOverviewPaneProps> = ({ compressor }) => {
  const metrics = compressor.metrics || {};
  const operational = metrics.operational as Record<string, unknown> | undefined;
  const sidecarRestErr = metrics.sidecar_rest_error as string | undefined;
  const online = compressor.is_online === true;
  const linkDot = online ? '●' : '○';
  const linkLabel = online ? 'ONLINE' : 'OFFLINE';

  return (
    <div
      className="alarm-pane terminal-box compressor-terminal-pane compressor-overview-pane"
      onClick={(e) => e.stopPropagation()}
    >
      <div className="terminal-box-header">
        <div className="terminal-box-top">
          <div className="terminal-box-title-row">
            <span>{asciiHeaderLeft('Compressor overview')}</span>
            <div className="pane-header-right-actions">
              <PollingStatusLight
                lastUpdatedAt={compressor.last_successful_poll_at || compressor.poll_timestamp}
                expectedIntervalMs={Math.max((compressor.poll_interval_seconds ?? 5) * 1000, 1000)}
                ariaLabel="Compressor telemetry freshness"
              />
              <span>┐</span>
            </div>
          </div>
        </div>
      </div>

      <div className="terminal-box-content">
        <div className="compressor-overview-body">
          <div className="compressor-pane-section">
            <div className="compressor-pane-section-title">Connection</div>
            <div className="terminal-kv-row">
              <span className="terminal-kv-label">Link</span>
              <span className={`terminal-kv-value ${online ? 'text-success' : 'text-error'}`}>
                <span className="terminal-status-dot" aria-hidden>
                  {linkDot}
                </span>
                {linkLabel}
              </span>
            </div>
            <div className="terminal-kv-row">
              <span className="terminal-kv-label">Status</span>
              <span className="terminal-kv-value">{statusBracket(compressor.status || '', online)}</span>
            </div>
            <div className="terminal-kv-row">
              <span className="terminal-kv-label">SC2 host</span>
              <span className="terminal-kv-value">{compressor.ip_address || '—'}</span>
            </div>
          </div>

          <div className="compressor-pane-section">
            <div className="compressor-pane-section-title">Sidecar</div>
            <div className="terminal-kv-row">
              <span className="terminal-kv-label">REST URL</span>
              <span className="terminal-kv-value text-dim">{compressor.sidecar_rest_base_url || '—'}</span>
            </div>
            <div className="terminal-kv-row">
              <span className="terminal-kv-label">MQTT root</span>
              <span className="terminal-kv-value text-dim">{compressor.mqtt_topic_root || '—'}</span>
            </div>
            <div className="terminal-kv-row">
              <span className="terminal-kv-label">Kaeser creds</span>
              <span className="terminal-kv-value">
                {compressor.kaeser_credentials_configured ? 'YES (env on save)' : 'NO'}
              </span>
            </div>
            {compressor.kaeser_connect_base_url && (
              <div className="terminal-kv-row">
                <span className="terminal-kv-label">Connect URL</span>
                <span className="terminal-kv-value text-dim">{compressor.kaeser_connect_base_url}</span>
              </div>
            )}
          </div>

          {compressor.error && (
            <div className="compressor-pane-section">
              <div className="compressor-pane-section-title">Error</div>
              <p className="compressor-error" style={{ margin: 0, fontSize: 'var(--font-sm)' }}>
                {compressor.error}
              </p>
              {(compressor.error.includes('Name or service not known') ||
                compressor.error.includes('service not known')) && (
                <p className="text-dim" style={{ margin: '0.5rem 0 0', fontSize: 'var(--font-xs)', lineHeight: 1.45 }}>
                  Usually kaeser-sc2-api is not running or the backend cannot resolve that hostname. Start with{' '}
                  <code style={{ fontSize: 'var(--font-xs)' }}>
                    docker compose -f docker-compose.dev.yml --profile kaeser up -d
                  </code>
                  , or set Sidecar REST to a reachable URL (e.g. host IP:3004).
                </p>
              )}
            </div>
          )}

          {sidecarRestErr && !compressor.error && (
            <div className="compressor-pane-section">
              <div className="compressor-pane-section-title">Sidecar REST</div>
              <p className="compressor-error" style={{ margin: 0, fontSize: 'var(--font-sm)' }}>
                {sidecarRestErr}
              </p>
            </div>
          )}

          <div className="compressor-pane-section">
            <div className="compressor-pane-section-title">Operational JSON</div>
            <p className="text-dim" style={{ margin: '0 0 var(--spacing-xs)', fontSize: 'var(--font-xs)', lineHeight: 1.45 }}>
              Last merged <code>metrics.operational</code> from MQTT + REST (debug).
            </p>
            {operational != null && Object.keys(operational).length > 0 ? (
              <pre className="compressor-registers-pre compressor-operational-json" aria-label="Raw operational JSON">
                {safeJsonStringify(operational)}
              </pre>
            ) : (
              <p className="text-dim" style={{ margin: 0, fontSize: 'var(--font-sm)' }}>
                No operational payload yet.
              </p>
            )}
          </div>
        </div>
      </div>

      <div className="terminal-box-footer">{asciiFooterLine(42)}</div>
    </div>
  );
};
