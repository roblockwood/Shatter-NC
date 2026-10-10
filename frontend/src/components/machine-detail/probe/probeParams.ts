// Copyright (C) 2024 Shatter-NC contributors
// SPDX-License-Identifier: AGPL-3.0-or-later

/**
 * Probe job-macro parameter editing: draft text ↔ number, validation, and the
 * per-machine/routine/mode localStorage cache of last-used values.
 */
import { isPoisonValue, isValidWcs, probeCatalog } from '../../../data/probeCatalog';

/** SIZE and TOOL can never be negative; WCS / distances / angles are signed. */
const UNSIGNED_MACROS = new Set(['904', '920']);
const INTEGER_MACROS = new Set(['900', '920']);
const POSITIVE_MACROS = new Set(['904']);

const COMPLETE_NUMBER = /^-?(\d+\.?\d*|\.\d+)$/;

export function isSignedMacro(macro: string): boolean {
  return !UNSIGNED_MACROS.has(macro);
}

export function isIntegerMacro(macro: string): boolean {
  return INTEGER_MACROS.has(macro);
}

export function defaultParamsFor(macros: string[]): Record<string, number> {
  const out: Record<string, number> = {};
  for (const m of macros) {
    if (m === '900') out[m] = 54;
    else if (m === '920') out[m] = 1;
    else if (m === '904') out[m] = 50;
    else if (m === '905' || m === '906' || m === '907') {
      out[m] = m === '905' ? 0 : m === '906' ? 120 : 240;
    } else out[m] = 10;
  }
  return out;
}

/**
 * Whether `text` is acceptable while typing — includes incomplete states like
 * `-`, `-.`, `1.` so a value can be entered character by character.
 */
export function isEditableDraft(macro: string, text: string): boolean {
  if (text.startsWith('-') && !isSignedMacro(macro)) return false;
  return isIntegerMacro(macro) ? /^-?\d*$/.test(text) : /^-?\d*\.?\d*$/.test(text);
}

/** Parse committed draft text; null while incomplete or not a valid number for the field. */
export function parseParamText(macro: string, text: string | undefined): number | null {
  const t = (text ?? '').trim();
  if (!COMPLETE_NUMBER.test(t)) return null;
  const n = Number(t);
  if (!Number.isFinite(n)) return null;
  if (isIntegerMacro(macro) && !Number.isInteger(n)) return null;
  return n;
}

/** Why a value cannot be written, or null when it is runnable. */
export function paramError(macro: string, value: number | null | undefined): string | null {
  if (value == null || !Number.isFinite(value)) return 'Enter a number';
  if (isIntegerMacro(macro) && !Number.isInteger(value)) return 'Must be a whole number';
  if (isPoisonValue(macro, value)) return `${value} is the poison value`;
  if (macro === '900' && !isValidWcs(value)) return 'WCS must be 54–59, or negative for G54.1 P';
  if (POSITIVE_MACROS.has(macro) && value <= 0) return 'Must be greater than 0';
  if (macro === '920' && value < 1) return 'Tool must be 1 or more';
  return null;
}

export function formatParam(value: number): string {
  return String(Number(value.toFixed(6)));
}

export function toggleSign(text: string): string {
  return text.startsWith('-') ? text.slice(1) : `-${text}`;
}

/** Spin-button step from the current draft (incomplete drafts step from 0). */
export function stepParam(macro: string, text: string | undefined, delta: number): string {
  let next = (parseParamText(macro, text) ?? 0) + delta;
  if (!isSignedMacro(macro) && next < 0) next = 0;
  return formatParam(next);
}

export function parseParams(text: Record<string, string>): Record<string, number> {
  const out: Record<string, number> = {};
  for (const [macro, t] of Object.entries(text)) {
    const n = parseParamText(macro, t);
    if (n != null) out[macro] = n;
  }
  return out;
}

const CACHE_PREFIX = 'shatter.probeParams';

export function probeParamsCacheKey(
  machineId: number | string,
  routineId: string,
  mode: string
): string {
  return `${CACHE_PREFIX}.${machineId}.${routineId}.${mode}`;
}

function defaultStorage(): Storage | null {
  try {
    return typeof window !== 'undefined' ? window.localStorage : null;
  } catch {
    return null;
  }
}

/**
 * Last-used values for this machine + routine + mode. Only required macros whose
 * cached value passes {@link paramError} are returned — a stale, corrupt, or
 * hand-edited entry falls back to the default instead of reaching a macro write.
 */
export function loadCachedParams(
  machineId: number | string,
  routineId: string,
  mode: string,
  required: string[],
  storage: Storage | null = defaultStorage()
): Record<string, number> {
  const out: Record<string, number> = {};
  if (!storage) return out;
  try {
    const raw = storage.getItem(probeParamsCacheKey(machineId, routineId, mode));
    if (!raw) return out;
    const parsed: unknown = JSON.parse(raw);
    const values =
      parsed && typeof parsed === 'object' && 'values' in parsed
        ? (parsed as { values: unknown }).values
        : null;
    if (!values || typeof values !== 'object') return out;
    for (const macro of required) {
      const v = (values as Record<string, unknown>)[macro];
      if (typeof v === 'number' && paramError(macro, v) == null) out[macro] = v;
    }
  } catch {
    // Corrupt JSON / storage access denied — defaults win.
  }
  return out;
}

export function saveCachedParams(
  machineId: number | string,
  routineId: string,
  mode: string,
  params: Record<string, number>,
  storage: Storage | null = defaultStorage()
): void {
  if (!storage) return;
  const values: Record<string, number> = {};
  for (const [macro, v] of Object.entries(params)) {
    if (macro in probeCatalog.fields && paramError(macro, v) == null) values[macro] = v;
  }
  try {
    storage.setItem(
      probeParamsCacheKey(machineId, routineId, mode),
      JSON.stringify({ v: 1, savedAt: new Date().toISOString(), values })
    );
  } catch {
    // Quota / private mode — caching is best-effort.
  }
}

/** Draft text for a routine: cached last-used values, else catalog defaults. */
export function initialParamText(
  machineId: number | string,
  routineId: string,
  mode: string,
  required: string[],
  storage: Storage | null = defaultStorage()
): Record<string, string> {
  const defaults = defaultParamsFor(required);
  const cached = loadCachedParams(machineId, routineId, mode, required, storage);
  const out: Record<string, string> = {};
  for (const macro of required) {
    out[macro] = formatParam(cached[macro] ?? defaults[macro]);
  }
  return out;
}
