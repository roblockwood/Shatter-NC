/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_APP_VERSION?: string;
  /** Docker build channel: "beta" for integration images; empty for stable/local dev */
  readonly VITE_RELEASE_CHANNEL?: string;
  readonly VITE_DEMO_MODE?: string;
  readonly VITE_API_URL?: string;
  /** Rare deploy default when `/tablet` has no query/localStorage yet (multi-tablet uses localStorage or `/tablet/setup`) */
  readonly VITE_TABLET_MACHINE_ID?: string;
  /** Optional default compressor id for compressor kiosk (`/tablet/compressor/...`) when no query/storage */
  readonly VITE_TABLET_COMPRESSOR_ID?: string;
  /** Override PWA manifest start_url only if needed (default `./tablet`) */
  readonly VITE_PWA_START_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
