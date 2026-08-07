export const IS_DEMO_MODE = import.meta.env.VITE_DEMO_MODE === 'true';

/** GitHub Pages project-site repo segment (project site at /Shatter-NC/). */
export const GITHUB_PAGES_REPO = 'Shatter-NC';

/** Absolute path to the demo SPA on GitHub Pages, e.g. `/Shatter-NC/demo/`. */
export const DEMO_PAGES_BASE = `/${GITHUB_PAGES_REPO}/demo/`;

/** Absolute path to the install kit on GitHub Pages, e.g. `/Shatter-NC/install/`. */
export const INSTALL_PAGES_BASE = `/${GITHUB_PAGES_REPO}/install/`;

/** Absolute path to the GitHub Pages landing page, e.g. `/Shatter-NC/`. */
export const SITE_PAGES_BASE = `/${GITHUB_PAGES_REPO}/`;

/**
 * Install kit URL for the demo banner.
 * Always root-absolute so it works from nested SPA routes like `/files`.
 */
export function demoInstallUrl(): string {
  return INSTALL_PAGES_BASE;
}
