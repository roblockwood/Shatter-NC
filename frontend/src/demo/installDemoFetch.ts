import { demoFetch } from './demoFetchRouter';

let installed = false;
let nativeFetch: typeof fetch | null = null;

export function installDemoFetch(): void {
  if (installed || typeof window === 'undefined') return;
  installed = true;
  nativeFetch = window.fetch.bind(window);
  window.fetch = ((input: RequestInfo | URL, init?: RequestInit) =>
    demoFetch(input, init, nativeFetch!)) as typeof fetch;
}
