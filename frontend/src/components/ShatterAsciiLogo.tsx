import { useEffect, useState } from 'react';
import { SHATTER_ASCII_LOGO } from '../pages/tablet/shatterAsciiLogo';
import './ShatterAsciiLogo.css';

/** Align with desktop logo metrics (`terminal.css` / `--font-sm`) when requesting webfonts */
const LOGO_FONT_PX = 12;

export type ShatterAsciiLogoVariant = 'loading' | 'empty' | 'screensaver';

function preClassName(variant: ShatterAsciiLogoVariant): string {
  if (variant === 'screensaver') return 'tablet-screensaver-art';
  return 'ascii-art';
}

type ShatterAsciiLogoProps = {
  variant: ShatterAsciiLogoVariant;
};

/**
 * SHATTER block logo — always `<pre>` + webfonts (no canvas). Waits for Noto / IBM Plex to load
 * before fading in so Android does not paint mixed fallback fonts (broken column alignment).
 */
export function ShatterAsciiLogo({ variant }: ShatterAsciiLogoProps) {
  const [fontsReady, setFontsReady] = useState(() => {
    if (typeof document === 'undefined') return false;
    return document.fonts.status === 'loaded';
  });

  useEffect(() => {
    let cancelled = false;

    const run = async () => {
      try {
        await Promise.all([
          document.fonts.load(`400 ${LOGO_FONT_PX}px "Noto Sans Mono"`),
          document.fonts.load(`400 ${LOGO_FONT_PX}px "IBM Plex Mono"`),
        ]);
        await document.fonts.ready;
      } catch {
        /* still try to show after ready */
        await document.fonts.ready.catch(() => {});
      }
      if (!cancelled) setFontsReady(true);
    };

    void run();

    return () => {
      cancelled = true;
    };
  }, []);

  const preClass = preClassName(variant);

  return (
    <span
      className={[
        'shatter-logo-font-wrap',
        fontsReady ? 'shatter-logo-font-wrap--ready' : '',
      ]
        .filter(Boolean)
        .join(' ')}
    >
      <pre className={preClass}>{SHATTER_ASCII_LOGO}</pre>
    </span>
  );
}
