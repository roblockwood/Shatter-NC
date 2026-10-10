// Copyright (C) 2024 Shatter-NC contributors
// SPDX-License-Identifier: AGPL-3.0-or-later

import { beforeEach, describe, expect, it } from 'vitest';
import {
  initialParamText,
  isEditableDraft,
  loadCachedParams,
  paramError,
  parseParamText,
  probeParamsCacheKey,
  saveCachedParams,
  stepParam,
  toggleSign,
} from '../components/machine-detail/probe/probeParams';

describe('probeParams drafts', () => {
  it('accepts intermediate negative drafts for signed distances', () => {
    for (const text of ['', '-', '-1', '-1.', '-1.5', '-.5', '10']) {
      expect(isEditableDraft('901', text)).toBe(true);
    }
    expect(isEditableDraft('903', '-')).toBe(true);
    expect(isEditableDraft('901', '1-')).toBe(false);
    expect(isEditableDraft('901', 'abc')).toBe(false);
  });

  it('keeps integer-only and non-negative constraints', () => {
    expect(isEditableDraft('900', '-3')).toBe(true);
    expect(isEditableDraft('900', '54.5')).toBe(false);
    expect(isEditableDraft('920', '-1')).toBe(false);
    expect(isEditableDraft('904', '-')).toBe(false);
    expect(isEditableDraft('904', '12.7')).toBe(true);
  });

  it('parses only complete numbers', () => {
    expect(parseParamText('901', '-10')).toBe(-10);
    expect(parseParamText('901', '-1.')).toBe(-1);
    expect(parseParamText('901', '-.5')).toBe(-0.5);
    expect(parseParamText('901', '-')).toBeNull();
    expect(parseParamText('901', '')).toBeNull();
    expect(parseParamText('900', '54.5')).toBeNull();
  });

  it('validates field rules', () => {
    expect(paramError('901', -10)).toBeNull();
    expect(paramError('903', -25.4)).toBeNull();
    expect(paramError('900', -3)).toBeNull();
    expect(paramError('900', 54)).toBeNull();
    expect(paramError('900', 60)).not.toBeNull();
    expect(paramError('901', 999)).not.toBeNull(); // poison
    expect(paramError('904', -5)).not.toBeNull();
    expect(paramError('904', 0)).not.toBeNull();
    expect(paramError('920', 0)).not.toBeNull();
    expect(paramError('901', null)).not.toBeNull();
  });

  it('steps and toggles sign', () => {
    expect(stepParam('901', '0', -1)).toBe('-1');
    expect(stepParam('901', '-', 1)).toBe('1');
    expect(stepParam('901', '10.3', -1)).toBe('9.3');
    expect(stepParam('904', '0', -1)).toBe('0');
    expect(toggleSign('10')).toBe('-10');
    expect(toggleSign('-10')).toBe('10');
    expect(toggleSign('')).toBe('-');
  });
});

describe('probeParams cache', () => {
  beforeEach(() => localStorage.clear());

  it('round-trips per machine + routine + mode', () => {
    saveCachedParams(1, 'corner_xyz', 'probe', { '900': 55, '901': -10, '902': 12, '903': -5 });
    expect(localStorage.getItem(probeParamsCacheKey(1, 'corner_xyz', 'probe'))).toBeTruthy();
    expect(
      loadCachedParams(1, 'corner_xyz', 'probe', ['900', '901', '902', '903'])
    ).toEqual({ '900': 55, '901': -10, '902': 12, '903': -5 });
  });

  it('does not carry values across machines, routines, or modes', () => {
    saveCachedParams(1, 'corner_xyz', 'probe', { '901': -10 });
    expect(loadCachedParams(2, 'corner_xyz', 'probe', ['901'])).toEqual({});
    expect(loadCachedParams(1, 'corner_xy', 'probe', ['901'])).toEqual({});
    expect(loadCachedParams(1, 'corner_xyz', 'measure', ['901'])).toEqual({});
  });

  it('drops invalid / poisoned / corrupt cache entries', () => {
    const key = probeParamsCacheKey(1, 'corner_xyz', 'probe');
    localStorage.setItem(
      key,
      JSON.stringify({ v: 1, values: { '900': 0, '901': 999, '902': 'x', '903': -4 } })
    );
    expect(loadCachedParams(1, 'corner_xyz', 'probe', ['900', '901', '902', '903'])).toEqual({
      '903': -4,
    });
    localStorage.setItem(key, '{not json');
    expect(loadCachedParams(1, 'corner_xyz', 'probe', ['901'])).toEqual({});
  });

  it('initial text uses cache, else defaults', () => {
    expect(initialParamText(1, 'corner_xyz', 'probe', ['900', '901'])).toEqual({
      '900': '54',
      '901': '10',
    });
    saveCachedParams(1, 'corner_xyz', 'probe', { '901': -7.5 });
    expect(initialParamText(1, 'corner_xyz', 'probe', ['900', '901'])).toEqual({
      '900': '54',
      '901': '-7.5',
    });
  });
});
