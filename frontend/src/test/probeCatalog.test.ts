import { describe, expect, it } from 'vitest';
import {
  assessMacroFreshness,
  isPoisonValue,
  isValidWcs,
  probeCatalog,
  requiredMacros,
  resolveProgram,
} from '../data/probeCatalog';

describe('probeCatalog', () => {
  it('resolves corner XYZ probe macros and program', () => {
    const entry = resolveProgram('corner_xyz', 'probe');
    expect(entry?.program).toBe(8110);
    expect(requiredMacros('corner_xyz', 'probe')).toEqual(['900', '901', '902', '903']);
  });

  it('resolves inside diameter measure', () => {
    expect(resolveProgram('diameter_inside', 'measure')?.program).toBe(8216);
    expect(requiredMacros('diameter_inside', 'measure')).toEqual(['900', '904']);
  });

  it('resolves 3-point outside fields', () => {
    expect(requiredMacros('three_point_outside', 'probe')).toEqual([
      '900',
      '903',
      '904',
      '905',
      '906',
      '907',
    ]);
  });

  it('tool_length has probe only', () => {
    expect(resolveProgram('tool_length', 'probe')?.program).toBe(8100);
    expect(resolveProgram('tool_length', 'measure')).toBeNull();
  });

  it('detects poison and wcs rules', () => {
    expect(isPoisonValue('900', 0)).toBe(true);
    expect(isPoisonValue('901', 999)).toBe(true);
    expect(isValidWcs(54)).toBe(true);
    expect(isValidWcs(0)).toBe(false);
    expect(isValidWcs(60)).toBe(false);
  });

  it('assesses macro freshness', () => {
    const required = ['900', '904'];
    expect(
      assessMacroFreshness(required, { '900': 54, '904': 50 }, { '900': 0, '904': 999 })
    ).toBe('POISONED');
    expect(
      assessMacroFreshness(required, { '900': 54, '904': 50 }, { '900': 54, '904': 50 })
    ).toBe('FRESH');
    expect(
      assessMacroFreshness(required, { '900': 54, '904': 50 }, { '900': 55, '904': 50 })
    ).toBe('STALE');
  });

  it('catalog has expected categories', () => {
    const ids = probeCatalog.categories.map((c) => c.id);
    expect(ids).toContain('corner');
    expect(ids).toContain('diameter');
    expect(probeCatalog.routines.length).toBeGreaterThanOrEqual(20);
  });

  it('gate program and target macro are set', () => {
    expect(probeCatalog.gate_program).toBe(8099);
    expect(probeCatalog.target_macro).toBe(908);
    expect(probeCatalog.poison['908']).toBe(0);
  });
});
