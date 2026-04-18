import { TERMINAL_RULE_FILL } from '../utils/terminalAsciiRule';

/**
 * Horizontal rules for compact machine/compressor cards — same pattern as ToolsPane:
 * ├ + dash fill (clipped to width) + ┤.
 */
export const MACHINE_CARD_TERMINAL_RULE_FILL = TERMINAL_RULE_FILL;

export function MachineCardAsciiDivider({ variant = 'thick' }: { variant?: 'thick' | 'thin' }) {
  const className =
    variant === 'thin'
      ? 'machine-card-divider-row machine-card-divider-row--thin'
      : 'machine-card-divider-row';

  return (
    <div className={className} aria-hidden>
      <span className="machine-card-divider-cap">├</span>
      <span className="machine-card-divider-fill">{MACHINE_CARD_TERMINAL_RULE_FILL}</span>
      <span className="machine-card-divider-cap">┤</span>
    </div>
  );
}
