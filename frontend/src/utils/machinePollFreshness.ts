/** Fast-poll freshness for status/alarms/panel: last successful controller poll (falls back to legacy poll_timestamp). */
export function fastPollLastSuccessAt(machine: {
  last_successful_poll_at?: string | null;
  poll_timestamp: string;
}): string | null | undefined {
  if (machine.last_successful_poll_at !== undefined) {
    return machine.last_successful_poll_at;
  }
  return machine.poll_timestamp;
}
