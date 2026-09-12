/**
 * Blum V4A probe routine catalog (mirrors backend/app/data/probe_catalog.json).
 */
import catalogJson from '../data/probe_catalog.json';

export type ProbeMode = 'probe' | 'measure';

export interface ProbeFieldMeta {
  key: string;
  label: string;
  unit: string;
  help?: string;
}

export interface ProbeModeEntry {
  program: number;
  macros: string[];
}

export type ProbeViewPlane = 'xy' | 'xz' | 'yz' | 'tool';

export interface ProbeRoutine {
  id: string;
  category: string;
  label: string;
  glyph_id: string;
  view: ProbeViewPlane;
  prerequisites?: string;
  field_labels?: Record<string, string>;
  modes: Partial<Record<ProbeMode, ProbeModeEntry>>;
}

export interface ProbeCatalog {
  version: number;
  poison: Record<string, number>;
  result_macros: number[];
  gate_program: number;
  target_macro: number;
  fields: Record<string, ProbeFieldMeta>;
  categories: { id: string; label: string }[];
  routines: ProbeRoutine[];
}

export const probeCatalog = catalogJson as ProbeCatalog;

export function getRoutinesForCategory(categoryId: string): ProbeRoutine[] {
  return probeCatalog.routines.filter((r) => r.category === categoryId);
}

export function getRoutine(routineId: string): ProbeRoutine | undefined {
  return probeCatalog.routines.find((r) => r.id === routineId);
}

export function resolveProgram(
  routineId: string,
  mode: ProbeMode
): ProbeModeEntry | null {
  const routine = getRoutine(routineId);
  if (!routine) return null;
  return routine.modes[mode] ?? null;
}

export function requiredMacros(routineId: string, mode: ProbeMode): string[] {
  return resolveProgram(routineId, mode)?.macros ?? [];
}

export function fieldLabelFor(
  routine: ProbeRoutine,
  macro: string,
  fallback?: string
): string {
  const override = routine.field_labels?.[macro];
  if (override) return override;
  return probeCatalog.fields[macro]?.label ?? fallback ?? `#${macro}`;
}

export function isPoisonValue(macro: string, value: number | null | undefined): boolean {
  if (value == null || Number.isNaN(value)) return false;
  const poison = probeCatalog.poison[macro];
  if (poison === undefined) return false;
  return Math.abs(value - poison) < 1e-9;
}

export function isValidWcs(value: number): boolean {
  if (!Number.isInteger(value)) return false;
  if (Math.abs(value - 0) < 1e-9) return false;
  if (value >= 54 && value <= 59) return true;
  if (value <= -1) return true;
  return false;
}

/** Macro freshness vs form values for required macros. */
export type MacroFreshness = 'POISONED' | 'STALE' | 'FRESH' | 'UNKNOWN';

export function assessMacroFreshness(
  required: string[],
  formValues: Record<string, number>,
  liveMacros?: Record<string, number>
): MacroFreshness {
  if (!required.length) return 'UNKNOWN';
  if (!liveMacros) return 'UNKNOWN';

  let anyPoison = false;
  let allMatch = true;
  let anyMissing = false;

  for (const macro of required) {
    const live = liveMacros[macro] ?? liveMacros[String(Number(macro))];
    const form = formValues[macro];
    if (live == null) {
      anyMissing = true;
      continue;
    }
    if (isPoisonValue(macro, live)) {
      anyPoison = true;
    }
    if (form == null || Math.abs(live - form) > 1e-4) {
      allMatch = false;
    }
  }

  if (anyPoison) return 'POISONED';
  if (anyMissing) return 'UNKNOWN';
  if (allMatch) return 'FRESH';
  return 'STALE';
}
