/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_APP_VERSION?: string;
  readonly VITE_API_URL?: string;
  /** Fallback CNC machine id for `/tablet` kiosk when URL omits an id */
  readonly VITE_TABLET_MACHINE_ID?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
