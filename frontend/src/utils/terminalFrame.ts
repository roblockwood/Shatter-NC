/**
 * ASCII terminal frame segments (see docs/UX_DESIGN_GUIDE.md — box drawing).
 * Left segment pairs with <div class="pane-header-right-actions">…</div><span>┐</span>
 */
export function asciiHeaderLeft(title: string, minDashes = 8): string {
  const prefix = `┌─ ${title.trim().toUpperCase()} `;
  const dashes = Math.max(minDashes, 52 - prefix.length);
  return `${prefix}${'─'.repeat(dashes)}`;
}

export const asciiFooterLine = (width = 42): string => `└${'─'.repeat(width)}┘`;
