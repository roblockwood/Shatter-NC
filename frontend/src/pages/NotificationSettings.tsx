import React, { useEffect, useState } from 'react';
import './NotificationSettings.css';
import { API_BASE_URL } from '../config/api';
import {
  listChannels,
  createChannel,
  updateChannel,
  deleteChannel,
  testChannel,
  listRules,
  createRule,
  updateRule,
  deleteRule,
  listLog,
} from '../api/notifications';
import type {
  NotificationChannel,
  NotificationRule,
  NotificationLogEntry,
} from '../api/notifications';

interface Machine {
  id: number;
  name: string;
}

type Tab = 'channels' | 'rules';

const TRIGGER_OPTIONS = [
  { value: JSON.stringify({ to_status: 'error' }), label: 'Error / Alarm' },
  { value: JSON.stringify({ from_status: 'operating', to_status: ['standby', 'stopped'] }), label: 'Cycle Complete' },
  { value: JSON.stringify({ any: true }), label: 'Any Status Change' },
  { value: JSON.stringify({ to_status: 'off' }), label: 'Machine Offline' },
];

function formatDate(iso: string): string {
  const d = new Date(iso);
  const date = d.toLocaleDateString(undefined, { month: 'numeric', day: 'numeric' });
  const time = d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' });
  return `${date} ${time}`;
}

function stableStringify(value: unknown): string {
  if (Array.isArray(value)) {
    return `[${value.map((item) => stableStringify(item)).join(',')}]`;
  }
  if (value && typeof value === 'object') {
    const entries = Object.entries(value as Record<string, unknown>).sort(([a], [b]) => a.localeCompare(b));
    return `{${entries.map(([k, v]) => `${JSON.stringify(k)}:${stableStringify(v)}`).join(',')}}`;
  }
  return JSON.stringify(value);
}

function baseTriggerConfig(triggerConfig: Record<string, unknown>): Record<string, unknown> {
  const { exclude_alarm_codes: _excludeCodes, ...baseConfig } = triggerConfig;
  return baseConfig;
}

function findTriggerOption(triggerConfig: Record<string, unknown>) {
  const normalized = stableStringify(baseTriggerConfig(triggerConfig));
  return TRIGGER_OPTIONS.find((option) => {
    const optionConfig = JSON.parse(option.value) as Record<string, unknown>;
    return stableStringify(optionConfig) === normalized;
  });
}

const BLANK_CHANNEL = { name: '', channelType: 'email' as 'email' | 'sms', to: '', smtpHost: '', smtpPort: '587', username: '', password: '' };
const BLANK_RULE = { name: '', machineId: '', trigger: TRIGGER_OPTIONS[0].value, channelIds: [] as number[], excludeAlarmCodes: '' };

type ChFormState = typeof BLANK_CHANNEL;
type RuleFormState = typeof BLANK_RULE;

interface ChannelFormProps {
  form: ChFormState;
  setForm: React.Dispatch<React.SetStateAction<ChFormState>>;
  isEdit: boolean;
  onSubmit: (e: React.FormEvent) => void;
  onCancel: () => void;
}

function _ChannelForm({ form, setForm, isEdit, onSubmit, onCancel }: ChannelFormProps) {
  return (
    <form className="notify-form" onSubmit={onSubmit}>
      <div className="notify-form-title">{isEdit ? 'Edit Channel' : 'New Email Channel'}</div>
      {!isEdit && (
        <div className="notify-hint">
          Use your email address for alerts, or a carrier gateway for SMS:<br />
          AT&amp;T: 5551234567@txt.att.net &nbsp; T-Mobile: 5551234567@tmomail.net &nbsp; Verizon: 5551234567@vtext.com
        </div>
      )}
      <div className="notify-field">
        <label>Name</label>
        <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="My Phone" required />
      </div>
      <div className="notify-field">
        <label>Recipient Address</label>
        <input value={form.to} onChange={(e) => setForm({ ...form, to: e.target.value })} placeholder="5551234567@tmomail.net" required />
      </div>
      <div className="notify-row">
        <div className="notify-field">
          <label>SMTP Host</label>
          <input value={form.smtpHost} onChange={(e) => setForm({ ...form, smtpHost: e.target.value })} placeholder="smtp.gmail.com" />
        </div>
        <div className="notify-field">
          <label>SMTP Port</label>
          <input value={form.smtpPort} onChange={(e) => setForm({ ...form, smtpPort: e.target.value })} placeholder="587" />
        </div>
      </div>
      <div className="notify-row">
        <div className="notify-field">
          <label>Username</label>
          <input value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} placeholder="your.email@gmail.com" />
        </div>
        <div className="notify-field">
          <label>Password / App Password</label>
          <input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} placeholder={isEdit ? '(unchanged if blank)' : 'Gmail App Password'} />
        </div>
      </div>
      <div style={{ display: 'flex', gap: 'var(--spacing-sm)' }}>
        <button type="submit" className="notify-btn primary">[ save ]</button>
        <button type="button" className="notify-btn" onClick={onCancel}>[ cancel ]</button>
      </div>
    </form>
  );
}

interface RuleFormProps {
  form: RuleFormState;
  setForm: React.Dispatch<React.SetStateAction<RuleFormState>>;
  isEdit: boolean;
  onSubmit: (e: React.FormEvent) => void;
  onCancel: () => void;
  channels: NotificationChannel[];
  machines: Machine[];
  onToggleChannel: (id: number) => void;
}

function _RuleForm({ form, setForm, isEdit, onSubmit, onCancel, channels, machines, onToggleChannel }: RuleFormProps) {
  return (
    <form className="notify-form" onSubmit={onSubmit}>
      <div className="notify-form-title">{isEdit ? 'Edit Rule' : 'New Notification Rule'}</div>
      <div className="notify-field">
        <label>Rule Name</label>
        <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Error alert" required />
      </div>
      <div className="notify-row">
        <div className="notify-field">
          <label>Machine</label>
          <select value={form.machineId} onChange={(e) => setForm({ ...form, machineId: e.target.value })}>
            <option value="">All machines</option>
            {machines.map((m) => (
              <option key={m.id} value={m.id}>{m.name}</option>
            ))}
          </select>
        </div>
        <div className="notify-field">
          <label>Trigger</label>
          <select value={form.trigger} onChange={(e) => setForm({ ...form, trigger: e.target.value })}>
            {TRIGGER_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </div>
      </div>
      <div className="notify-field">
        <label>Channels (select one or more)</label>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          {channels.map((ch) => (
            <label key={ch.id} className="notify-toggle">
              <input
                type="checkbox"
                checked={form.channelIds.includes(ch.id)}
                onChange={() => onToggleChannel(ch.id)}
              />
              {ch.name}
            </label>
          ))}
        </div>
      </div>
      <div style={{ display: 'flex', gap: 'var(--spacing-sm)' }}>
        <button type="submit" className="notify-btn primary">[ save ]</button>
        <button type="button" className="notify-btn" onClick={onCancel}>[ cancel ]</button>
      </div>
    </form>
  );
}

export function NotificationSettings() {
  const [tab, setTab] = useState<Tab>('channels');
  const [machines, setMachines] = useState<Machine[]>([]);
  const [channels, setChannels] = useState<NotificationChannel[]>([]);
  const [rules, setRules] = useState<NotificationRule[]>([]);
  const [log, setLog] = useState<NotificationLogEntry[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Channel form — null = hidden, 0 = new, >0 = editing that id
  const [editingChannelId, setEditingChannelId] = useState<number | null>(null);
  const [chForm, setChForm] = useState(BLANK_CHANNEL);

  // Rule form — null = hidden, 0 = new, >0 = editing that id
  const [editingRuleId, setEditingRuleId] = useState<number | null>(null);
  const [ruleForm, setRuleForm] = useState(BLANK_RULE);

  // Test feedback per channel
  const [testStatus, setTestStatus] = useState<Record<number, string>>({});

  useEffect(() => { fetchAll(); }, []);

  async function fetchAll() {
    try {
      const [ch, ru, lg] = await Promise.all([listChannels(), listRules(), listLog({ limit: 20 })]);
      setChannels(ch);
      setRules(ru);
      setLog(lg);
    } catch (e) {
      // Show error but keep existing state — don't blank the lists on a transient failure
      setError(`Failed to refresh: ${String(e)}`);
    }
    try {
      const res = await fetch(`${API_BASE_URL}/api/machines`);
      if (res.ok) setMachines(await res.json());
    } catch (_) { /* no-op */ }
  }

  // --- Channel form helpers ---

  function openNewChannel() {
    setChForm(BLANK_CHANNEL);
    setEditingChannelId(0);
  }

  function openEditChannel(ch: NotificationChannel) {
    const cfg = ch.config as Record<string, unknown>;
    setChForm({
      name: ch.name,
      channelType: (ch.channel_type as 'email' | 'sms') ?? 'email',
      to: String(cfg.to ?? ''),
      smtpHost: String(cfg.smtp_host ?? ''),
      smtpPort: String(cfg.smtp_port ?? '587'),
      username: String(cfg.username ?? ''),
      password: String(cfg.password ?? ''),
    });
    setEditingChannelId(ch.id);
  }

  function closeChannelForm() { setEditingChannelId(null); }

  function chConfig() {
    if (chForm.channelType === 'sms') {
      return { to: chForm.to };
    }
    return {
      to: chForm.to,
      ...(chForm.smtpHost ? { smtp_host: chForm.smtpHost } : {}),
      ...(chForm.smtpPort ? { smtp_port: parseInt(chForm.smtpPort) } : {}),
      ...(chForm.username ? { username: chForm.username } : {}),
      ...(chForm.password ? { password: chForm.password } : {}),
    };
  }

  async function handleSaveChannel(e: React.FormEvent) {
    e.preventDefault();
    try {
      if (editingChannelId === 0) {
        await createChannel({ name: chForm.name, channel_type: chForm.channelType, config: chConfig(), enabled: true });
      } else if (editingChannelId != null) {
        await updateChannel(editingChannelId, { name: chForm.name, channel_type: chForm.channelType, config: chConfig() });
      }
      closeChannelForm();
      fetchAll();
    } catch (e) { setError(String(e)); }
  }

  async function handleToggleChannel(ch: NotificationChannel) {
    try { await updateChannel(ch.id, { enabled: !ch.enabled }); fetchAll(); }
    catch (e) { setError(String(e)); }
  }

  async function handleDeleteChannel(id: number) {
    if (!confirm('Delete this channel?')) return;
    try { await deleteChannel(id); fetchAll(); }
    catch (e) { setError(String(e)); }
  }

  async function handleTestChannel(id: number) {
    setTestStatus((s) => ({ ...s, [id]: 'sending...' }));
    try {
      const result = await testChannel(id);
      setTestStatus((s) => ({ ...s, [id]: result.status === 'sent' ? 'sent!' : `failed: ${result.error}` }));
      fetchAll();
    } catch (e) { setTestStatus((s) => ({ ...s, [id]: `error: ${String(e)}` })); }
  }

  // --- Rule form helpers ---

  function openNewRule() {
    setRuleForm(BLANK_RULE);
    setEditingRuleId(0);
  }

  function openEditRule(rule: NotificationRule) {
    const triggerConfig = rule.trigger_config as Record<string, unknown>;
    const { exclude_alarm_codes: excludeCodes, ...baseConfig } = triggerConfig;
    const matchedTrigger = findTriggerOption(triggerConfig);
    setRuleForm({
      name: rule.name,
      machineId: rule.machine_id != null ? String(rule.machine_id) : '',
      trigger: matchedTrigger?.value ?? JSON.stringify(baseConfig),
      channelIds: rule.channel_ids ?? [],
      excludeAlarmCodes: Array.isArray(excludeCodes) ? (excludeCodes as string[]).join(', ') : '',
    });
    setEditingRuleId(rule.id);
  }

  function closeRuleForm() { setEditingRuleId(null); }

  function toggleRuleChannel(id: number) {
    setRuleForm((prev) => ({
      ...prev,
      channelIds: prev.channelIds.includes(id)
        ? prev.channelIds.filter((x) => x !== id)
        : [...prev.channelIds, id],
    }));
  }

  async function handleSaveRule(e: React.FormEvent) {
    e.preventDefault();
    if (ruleForm.channelIds.length === 0) { setError('Select at least one channel'); return; }
    const baseTrigger = JSON.parse(ruleForm.trigger);
    const excludeCodes = ruleForm.excludeAlarmCodes
      .split(',')
      .map((s) => s.trim().toUpperCase().replace(/[^A-Z0-9]/g, ''))
      .filter(Boolean);
    if (excludeCodes.length > 0) baseTrigger.exclude_alarm_codes = excludeCodes;
    const payload = {
      name: ruleForm.name,
      machine_id: ruleForm.machineId ? parseInt(ruleForm.machineId) : null,
      trigger_type: 'status_change' as const,
      trigger_config: baseTrigger,
      channel_ids: ruleForm.channelIds,
    };
    try {
      if (editingRuleId === 0) {
        await createRule({ ...payload, enabled: true });
      } else if (editingRuleId != null) {
        await updateRule(editingRuleId, payload);
      }
      closeRuleForm();
      fetchAll();
    } catch (e) { setError(String(e)); }
  }

  async function handleToggleRule(rule: NotificationRule) {
    try { await updateRule(rule.id, { enabled: !rule.enabled }); fetchAll(); }
    catch (e) { setError(String(e)); }
  }

  async function handleDeleteRule(id: number) {
    if (!confirm('Delete this rule?')) return;
    try { await deleteRule(id); fetchAll(); }
    catch (e) { setError(String(e)); }
  }

  // --- Display helpers ---

  function channelName_(id: number | null): string {
    if (id == null) return '—';
    return channels.find((c) => c.id === id)?.name ?? `#${id}`;
  }

  function machineName_(id: number | null): string {
    if (id == null) return 'All machines';
    return (machines.find((m) => m.id === id)?.name ?? `Machine #${id}`).toUpperCase();
  }

  function triggerLabel(trigger_config: Record<string, unknown>): string {
    const match = findTriggerOption(trigger_config);
    return match?.label ?? JSON.stringify(trigger_config);
  }

  // --- Channel form JSX ---

  function ChannelForm() {
    const isEdit = editingChannelId !== 0;
    const isSms = chForm.channelType === 'sms';
    return (
      <form className="notify-form" onSubmit={handleSaveChannel}>
        <div className="notify-form-title">{isEdit ? 'Edit Channel' : 'New Channel'}</div>
        <div className="notify-field">
          <label>Channel Type</label>
          <div style={{ display: 'flex', gap: 'var(--spacing-sm)' }}>
            <label className="notify-toggle">
              <input type="radio" name="channelType" value="email" checked={chForm.channelType === 'email'} onChange={() => setChForm({ ...chForm, channelType: 'email' })} />
              Email / SMTP
            </label>
            <label className="notify-toggle">
              <input type="radio" name="channelType" value="sms" checked={chForm.channelType === 'sms'} onChange={() => setChForm({ ...chForm, channelType: 'sms' })} />
              SMS via Twilio
            </label>
          </div>
        </div>
        <div className="notify-field">
          <label>Name</label>
          <input value={chForm.name} onChange={(e) => setChForm({ ...chForm, name: e.target.value })} placeholder={isSms ? 'My Phone' : 'Work Email'} required />
        </div>
        {isSms ? (
          <>
            <div className="notify-hint">Enter your phone number in E.164 format (e.g. +19195551234). Requires Twilio credentials configured in environment variables.</div>
            <div className="notify-field">
              <label>Phone Number</label>
              <input value={chForm.to} onChange={(e) => setChForm({ ...chForm, to: e.target.value })} placeholder="+19195551234" required />
            </div>
          </>
        ) : (
          <>
            {!isEdit && (
              <div className="notify-hint">
                Use your email address for alerts, or a carrier gateway for SMS:<br />
                AT&amp;T: 5551234567@txt.att.net &nbsp; T-Mobile: 5551234567@tmomail.net &nbsp; Verizon: 5551234567@vtext.com
              </div>
            )}
            <div className="notify-field">
              <label>Recipient Address</label>
              <input value={chForm.to} onChange={(e) => setChForm({ ...chForm, to: e.target.value })} placeholder="5551234567@tmomail.net" required />
            </div>
            <div className="notify-row">
              <div className="notify-field">
                <label>SMTP Host</label>
                <input value={chForm.smtpHost} onChange={(e) => setChForm({ ...chForm, smtpHost: e.target.value })} placeholder="smtp.gmail.com" />
              </div>
              <div className="notify-field">
                <label>SMTP Port</label>
                <input value={chForm.smtpPort} onChange={(e) => setChForm({ ...chForm, smtpPort: e.target.value })} placeholder="587" />
              </div>
            </div>
            <div className="notify-row">
              <div className="notify-field">
                <label>Username</label>
                <input value={chForm.username} onChange={(e) => setChForm({ ...chForm, username: e.target.value })} placeholder="your.email@gmail.com" />
              </div>
              <div className="notify-field">
                <label>Password / App Password</label>
                <input type="password" value={chForm.password} onChange={(e) => setChForm({ ...chForm, password: e.target.value })} placeholder={isEdit ? '(unchanged if blank)' : 'Gmail App Password'} />
              </div>
            </div>
          </>
        )}
        <div style={{ display: 'flex', gap: 'var(--spacing-sm)' }}>
          <button type="submit" className="notify-btn primary">[ save ]</button>
          <button type="button" className="notify-btn" onClick={closeChannelForm}>[ cancel ]</button>
        </div>
      </form>
    );
  }

  // --- Rule form JSX ---

  function RuleForm() {
    const isEdit = editingRuleId !== 0;
    return (
      <form className="notify-form" onSubmit={handleSaveRule}>
        <div className="notify-form-title">{isEdit ? 'Edit Rule' : 'New Notification Rule'}</div>
        <div className="notify-field">
          <label>Rule Name</label>
          <input value={ruleForm.name} onChange={(e) => setRuleForm({ ...ruleForm, name: e.target.value })} placeholder="Error alert" required />
        </div>
        <div className="notify-row">
          <div className="notify-field">
            <label>Machine</label>
            <select value={ruleForm.machineId} onChange={(e) => setRuleForm({ ...ruleForm, machineId: e.target.value })}>
              <option value="">All machines</option>
              {machines.map((m) => (
                <option key={m.id} value={m.id}>{m.name}</option>
              ))}
            </select>
          </div>
          <div className="notify-field">
            <label>Trigger</label>
            <select value={ruleForm.trigger} onChange={(e) => setRuleForm({ ...ruleForm, trigger: e.target.value })}>
              {TRIGGER_OPTIONS.map((o) => (
                <option key={o.value} value={o.value}>{o.label}</option>
              ))}
            </select>
          </div>
        </div>
        <div className="notify-field">
          <label>Channels (select one or more)</label>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            {channels.map((ch) => (
              <label key={ch.id} className="notify-toggle">
                <input
                  type="checkbox"
                  checked={ruleForm.channelIds.includes(ch.id)}
                  onChange={() => toggleRuleChannel(ch.id)}
                />
                {ch.name}
              </label>
            ))}
          </div>
        </div>
        <div className="notify-field">
          <label>Suppress for alarm codes (optional)</label>
          <input
            value={ruleForm.excludeAlarmCodes}
            onChange={(e) => setRuleForm({ ...ruleForm, excludeAlarmCodes: e.target.value })}
            placeholder="e.g. EX0001, IO0518 — comma-separated; notification skipped when only these alarms are active"
          />
        </div>
        <div style={{ display: 'flex', gap: 'var(--spacing-sm)' }}>
          <button type="submit" className="notify-btn primary">[ save ]</button>
          <button type="button" className="notify-btn" onClick={closeRuleForm}>[ cancel ]</button>
        </div>
      </form>
    );
  }

  return (
    <div className="notify-page">
      <div className="notify-header">
        <div>
          <div className="notify-title">[ NOTIFICATIONS ]</div>
          <div className="notify-subtitle">Email and SMS alerts for machine status events</div>
        </div>
      </div>

      <div className="notify-divider">{'─'.repeat(80)}</div>

      {error && (
        <div className="notify-status-err">
          {error}{' '}
          <button className="notify-btn" onClick={() => { setError(null); fetchAll(); }}>[retry]</button>
          <button className="notify-btn" onClick={() => setError(null)}>[x]</button>
        </div>
      )}

      <div className="notify-tabs">
        <button className={`notify-tab${tab === 'channels' ? ' active' : ''}`} onClick={() => setTab('channels')}>
          [ CHANNELS ]
        </button>
        <button className={`notify-tab${tab === 'rules' ? ' active' : ''}`} onClick={() => setTab('rules')}>
          [ RULES ]
        </button>
      </div>

      {tab === 'channels' && (
        <div className="notify-section">
          {editingChannelId === null && (
            <div>
              <button className="notify-btn primary" onClick={openNewChannel}>[ + add channel ]</button>
            </div>
          )}

          {editingChannelId === 0 && ChannelForm()}

          {channels.length === 0 && editingChannelId === null && (
            <div className="notify-empty">No channels configured. Add one to start receiving alerts.</div>
          )}

          {channels.map((ch) => (
            <React.Fragment key={ch.id}>
              {editingChannelId === ch.id ? (
                ChannelForm()
              ) : (
                <div className="notify-card">
                  <div className="notify-card-header">
                    <div className="notify-card-title">{ch.name}</div>
                    <div className="notify-card-actions">
                      <label className="notify-toggle">
                        <input type="checkbox" checked={ch.enabled} onChange={() => handleToggleChannel(ch)} />
                        {ch.enabled ? 'enabled' : 'disabled'}
                      </label>
                      <button className="notify-btn" onClick={() => handleTestChannel(ch.id)}>[ test ]</button>
                      <button className="notify-btn" onClick={() => openEditChannel(ch)}>[ edit ]</button>
                      <button className="notify-btn danger" onClick={() => handleDeleteChannel(ch.id)}>[ delete ]</button>
                    </div>
                  </div>
                  <div className="notify-hint">
                    {ch.channel_type === 'sms' ? (
                      <>SMS (Twilio): {(ch.config as Record<string, string>).to ?? '—'}</>
                    ) : (
                      <>
                        To: {(ch.config as Record<string, string>).to ?? '—'}
                        {(ch.config as Record<string, string>).smtp_host && (
                          <> &nbsp;|&nbsp; SMTP: {(ch.config as Record<string, string>).smtp_host}:{(ch.config as Record<string, unknown>).smtp_port ?? 587}</>
                        )}
                      </>
                    )}
                  </div>
                  {testStatus[ch.id] && (
                    <div className={testStatus[ch.id].startsWith('sent') ? 'notify-status-ok' : 'notify-status-err'}>
                      {testStatus[ch.id]}
                    </div>
                  )}
                </div>
              )}
            </React.Fragment>
          ))}
        </div>
      )}

      {tab === 'rules' && (
        <div className="notify-section">
          {channels.length === 0 && (
            <div className="notify-hint">Add a channel first before creating rules.</div>
          )}
          {editingRuleId === null && (
            <div>
              <button className="notify-btn primary" onClick={openNewRule} disabled={channels.length === 0}>
                [ + add rule ]
              </button>
            </div>
          )}

          {editingRuleId === 0 && RuleForm()}

          {rules.length === 0 && editingRuleId === null && (
            <div className="notify-empty">No rules configured.</div>
          )}

          {rules.map((rule) => (
            <React.Fragment key={rule.id}>
              {editingRuleId === rule.id ? (
                RuleForm()
              ) : (
                <div className="notify-card">
                  <div className="notify-card-header">
                    <div className="notify-card-title">{rule.name}</div>
                    <div className="notify-card-actions">
                      <label className="notify-toggle">
                        <input type="checkbox" checked={rule.enabled} onChange={() => handleToggleRule(rule)} />
                        {rule.enabled ? 'enabled' : 'disabled'}
                      </label>
                      <button className="notify-btn" onClick={() => openEditRule(rule)}>[ edit ]</button>
                      <button className="notify-btn danger" onClick={() => handleDeleteRule(rule.id)}>[ delete ]</button>
                    </div>
                  </div>
                  <div className="notify-hint">
                    Machine: {machineName_(rule.machine_id)} &nbsp;|&nbsp;
                    Trigger: {triggerLabel(rule.trigger_config as Record<string, unknown>)} &nbsp;|&nbsp;
                    Channels: {rule.channel_ids.map(channelName_).join(', ') || '—'}
                  </div>
                </div>
              )}
            </React.Fragment>
          ))}
        </div>
      )}

      <div className="notify-divider">{'─'.repeat(80)}</div>
      <div className="notify-title" style={{ fontSize: 'var(--font-md)' }}>[ DELIVERY LOG ]</div>

      {log.length === 0 ? (
        <div className="notify-empty">No notifications sent yet.</div>
      ) : (
        <table className="notify-log-table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Machine</th>
              <th>Rule</th>
              <th>Channel</th>
              <th>Message</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {log.map((entry) => (
              <tr key={entry.id}>
                <td>{formatDate(entry.sent_at)}</td>
                <td>{machineName_(entry.machine_id)}</td>
                <td>{entry.rule_name || entry.event_type}</td>
                <td>{channelName_(entry.channel_id)}</td>
                <td className="notify-log-message">
                  {entry.message
                    ? entry.message.split('\n')[0].replace(/^Subject:\s*/i, '')
                    : '—'}
                </td>
                <td>
                  <span className={entry.status === 'sent' ? 'notify-log-sent' : 'notify-log-failed'}>
                    {entry.status}
                  </span>
                  {entry.error_message && (
                    <span className="notify-hint"> — {entry.error_message}</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
