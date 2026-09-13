// Copyright (C) 2024 Shatter-NC contributors
// SPDX-License-Identifier: AGPL-3.0-or-later

/** Mirror AlarmPane: stop_level 5..1 (5 highest). Default to 3 if missing/invalid. */
export function alarmStopLevel(alarm: { stop_level?: string }): number {
  const raw = alarm.stop_level;
  if (raw !== undefined && raw !== null && String(raw) !== '') {
    const level = parseInt(String(raw), 10);
    if (!Number.isNaN(level) && level >= 1 && level <= 5) {
      return level;
    }
  }
  return 3;
}
