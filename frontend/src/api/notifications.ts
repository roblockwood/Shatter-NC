import { API_BASE_URL, getApiErrorMessage } from '../config/api';

export type ChannelType = 'email' | 'sms';
export type TriggerType = 'status_change';

export interface NotificationChannel {
  id: number;
  name: string;
  channel_type: ChannelType;
  config: Record<string, unknown>;
  enabled: boolean;
  created_at: string;
}

export interface NotificationChannelCreate {
  name: string;
  channel_type: ChannelType;
  config: Record<string, unknown>;
  enabled?: boolean;
}

export interface NotificationChannelUpdate {
  name?: string;
  channel_type?: ChannelType;
  config?: Record<string, unknown>;
  enabled?: boolean;
}

export interface NotificationRule {
  id: number;
  name: string;
  machine_id: number | null;
  trigger_type: TriggerType;
  trigger_config: Record<string, unknown>;
  channel_ids: number[];
  enabled: boolean;
  created_at: string;
}

export interface NotificationRuleCreate {
  name: string;
  machine_id: number | null;
  trigger_type: TriggerType;
  trigger_config: Record<string, unknown>;
  channel_ids: number[];
  enabled?: boolean;
}

export interface NotificationRuleUpdate {
  name?: string;
  machine_id?: number | null;
  trigger_type?: TriggerType;
  trigger_config?: Record<string, unknown>;
  channel_ids?: number[];
  enabled?: boolean;
}

export interface NotificationLogEntry {
  id: number;
  rule_id: number | null;
  rule_name?: string | null;
  channel_id: number | null;
  machine_id: number | null;
  event_type: string;
  event_data: Record<string, unknown> | null;
  message: string | null;
  status: string;
  error_message: string | null;
  sent_at: string;
}

export interface TestResult {
  status: 'sent' | 'failed';
  error?: string;
}

// --- Channels ---

export async function listChannels(): Promise<NotificationChannel[]> {
  const res = await fetch(`${API_BASE_URL}/api/notifications/channels`);
  if (!res.ok) throw new Error(await getApiErrorMessage(res));
  return res.json();
}

export async function createChannel(data: NotificationChannelCreate): Promise<NotificationChannel> {
  const res = await fetch(`${API_BASE_URL}/api/notifications/channels`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(await getApiErrorMessage(res));
  return res.json();
}

export async function updateChannel(id: number, data: NotificationChannelUpdate): Promise<NotificationChannel> {
  const res = await fetch(`${API_BASE_URL}/api/notifications/channels/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(await getApiErrorMessage(res));
  return res.json();
}

export async function deleteChannel(id: number): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/api/notifications/channels/${id}`, { method: 'DELETE' });
  if (!res.ok) throw new Error(await getApiErrorMessage(res));
}

export async function testChannel(id: number): Promise<TestResult> {
  const res = await fetch(`${API_BASE_URL}/api/notifications/test/${id}`, { method: 'POST', headers: { 'Content-Type': 'application/json' } });
  if (!res.ok) throw new Error(await getApiErrorMessage(res));
  return res.json();
}

// --- Rules ---

export async function listRules(): Promise<NotificationRule[]> {
  const res = await fetch(`${API_BASE_URL}/api/notifications/rules`);
  if (!res.ok) throw new Error(await getApiErrorMessage(res));
  return res.json();
}

export async function createRule(data: NotificationRuleCreate): Promise<NotificationRule> {
  const res = await fetch(`${API_BASE_URL}/api/notifications/rules`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(await getApiErrorMessage(res));
  return res.json();
}

export async function updateRule(id: number, data: NotificationRuleUpdate): Promise<NotificationRule> {
  const res = await fetch(`${API_BASE_URL}/api/notifications/rules/${id}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(await getApiErrorMessage(res));
  return res.json();
}

export async function deleteRule(id: number): Promise<void> {
  const res = await fetch(`${API_BASE_URL}/api/notifications/rules/${id}`, { method: 'DELETE' });
  if (!res.ok) throw new Error(await getApiErrorMessage(res));
}

// --- Log ---

export async function listLog(params?: { machine_id?: number; limit?: number; offset?: number }): Promise<NotificationLogEntry[]> {
  const query = new URLSearchParams();
  if (params?.machine_id != null) query.set('machine_id', String(params.machine_id));
  if (params?.limit != null) query.set('limit', String(params.limit));
  if (params?.offset != null) query.set('offset', String(params.offset));
  const res = await fetch(`${API_BASE_URL}/api/notifications/log?${query}`);
  if (!res.ok) throw new Error(await getApiErrorMessage(res));
  return res.json();
}
