import type { ReactNode } from 'react';
import '../ui/TerminalBox.css';
import { TERMINAL_RULE_FILL } from '../../utils/terminalAsciiRule';

/**
 * Unified ┌─ title + clipped dash fill + optional right cluster + ┐ (matches ToolsPane / MachineCardAsciiDivider).
 */
export function PaneTerminalHeader({
  label,
  children,
}: {
  label: ReactNode;
  children?: ReactNode;
}) {
  return (
    <div className="terminal-box-header pane-terminal-header">
      <div className="terminal-box-top">
        <div className="terminal-box-title-row pane-terminal-title-row">
          <span className="pane-terminal-title-start">┌─ {label}</span>
          <span className="pane-terminal-title-fill" aria-hidden>
            {TERMINAL_RULE_FILL}
          </span>
          {children != null ? <div className="pane-header-right-actions">{children}</div> : null}
          <span className="pane-terminal-title-corner">┐</span>
        </div>
      </div>
    </div>
  );
}

/** Inner └──┘ row only (for nesting inside another panel shell). */
export function PaneTerminalFooterInner() {
  return (
    <div className="pane-terminal-footer-row">
      <span className="pane-terminal-footer-corner">└</span>
      <span className="pane-terminal-footer-fill" aria-hidden>
        {TERMINAL_RULE_FILL}
      </span>
      <span className="pane-terminal-footer-corner">┘</span>
    </div>
  );
}

export function PaneTerminalFooter() {
  return (
    <div className="terminal-box-footer pane-terminal-footer">
      <PaneTerminalFooterInner />
    </div>
  );
}
