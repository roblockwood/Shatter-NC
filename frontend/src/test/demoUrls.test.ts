import { describe, expect, it } from 'vitest';
import {
  DEMO_PAGES_BASE,
  INSTALL_PAGES_BASE,
  SITE_PAGES_BASE,
  demoInstallUrl,
} from '../config/demo';

describe('demo page URLs', () => {
  it('uses root-absolute GitHub Pages paths', () => {
    expect(DEMO_PAGES_BASE).toBe('/Shatter-NC/demo/');
    expect(INSTALL_PAGES_BASE).toBe('/Shatter-NC/install/');
    expect(SITE_PAGES_BASE).toBe('/Shatter-NC/');
  });

  it('install URL is root-absolute (not relative to SPA routes)', () => {
    expect(demoInstallUrl()).toBe('/Shatter-NC/install/');
    expect(demoInstallUrl().startsWith('/')).toBe(true);
    expect(demoInstallUrl()).not.toContain('/demo/');
  });
});
