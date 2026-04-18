/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_APP_VERSION?: string;
  readonly VITE_API_URL?: string;
  /** Rare deploy default when `/tablet` has no query/localStorage yet (multi-tablet uses localStorage or `/tablet/setup`) */
  readonly VITE_TABLET_MACHINE_ID?: string;
  /** Override PWA manifest start_url only if needed (default `./tablet`) */
  readonly VITE_PWA_START_URL?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
