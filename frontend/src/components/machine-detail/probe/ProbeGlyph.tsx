/**
 * Flat phosphor SVG glyphs for probe routine selection (compressor TileIcon style).
 * Inspired by Blum V4A APPLext overview; hand-drawn, not vendor art.
 */
import React from 'react';

const SW = 1.75;

function Frame({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <svg
      className={className ?? 'probe-glyph'}
      viewBox="0 0 24 24"
      aria-hidden
      fill="none"
      stroke="currentColor"
      strokeWidth={SW}
      strokeLinejoin="miter"
      strokeLinecap="square"
    >
      {children}
    </svg>
  );
}

/** Small stylus tip marker */
function Tip({ x, y }: { x: number; y: number }) {
  return <circle cx={x} cy={y} r={1.4} fill="currentColor" stroke="none" />;
}

export function ProbeGlyph({ glyphId, className }: { glyphId: string; className?: string }) {
  switch (glyphId) {
    case 'tool_length':
      return (
        <Frame className={className}>
          {/* Blum Z-Nano: base flange + body + flat measuring pad */}
          <ellipse cx="12" cy="20" rx="8" ry="2.2" />
          <path d="M4 20 L4 10 Q4 7 12 7 Q20 7 20 10 L20 20" />
          <ellipse cx="12" cy="7" rx="6" ry="1.8" />
          <ellipse cx="12" cy="5.2" rx="4.5" ry="1.3" />
          {/* tool tip approaching −Z */}
          <line x1="12" y1="1" x2="12" y2="4.2" />
          <Tip x={12} y={4.2} />
        </Frame>
      );
    case 'face_x_plus':
      return (
        <Frame className={className}>
          <rect x="12" y="6" width="8" height="12" />
          <line x1="4" y1="12" x2="11" y2="12" />
          <Tip x={11} y={12} />
        </Frame>
      );
    case 'face_x_minus':
      return (
        <Frame className={className}>
          <rect x="4" y="6" width="8" height="12" />
          <line x1="20" y1="12" x2="13" y2="12" />
          <Tip x={13} y={12} />
        </Frame>
      );
    case 'face_y_plus':
      return (
        <Frame className={className}>
          <rect x="6" y="4" width="12" height="8" />
          <line x1="12" y1="20" x2="12" y2="13" />
          <Tip x={12} y={13} />
        </Frame>
      );
    case 'face_y_minus':
      return (
        <Frame className={className}>
          <rect x="6" y="12" width="12" height="8" />
          <line x1="12" y1="4" x2="12" y2="11" />
          <Tip x={12} y={11} />
        </Frame>
      );
    case 'face_z':
      return (
        <Frame className={className}>
          <rect x="5" y="14" width="14" height="5" />
          <line x1="12" y1="4" x2="12" y2="13" />
          <Tip x={12} y={13} />
        </Frame>
      );
    case 'corner_xy':
      return (
        <Frame className={className}>
          <path d="M14 6 H20 V20 H8 V14" />
          <line x1="4" y1="10" x2="13" y2="10" />
          <line x1="10" y1="4" x2="10" y2="13" />
          <Tip x={10} y={10} />
        </Frame>
      );
    case 'corner_xz':
      return (
        <Frame className={className}>
          <path d="M6 18 H18 V10 H10 V18" />
          <line x1="4" y1="14" x2="9" y2="14" />
          <line x1="14" y1="4" x2="14" y2="9" />
          <Tip x={14} y={10} />
        </Frame>
      );
    case 'corner_xyz':
      return (
        <Frame className={className}>
          <path d="M14 8 H20 V20 H8 V14" />
          <line x1="4" y1="10" x2="13" y2="10" />
          <line x1="10" y1="4" x2="10" y2="13" />
          <line x1="10" y1="10" x2="10" y2="16" />
          <Tip x={10} y={10} />
        </Frame>
      );
    case 'corner_yz':
      return (
        <Frame className={className}>
          <path d="M6 8 V20 H18 V12 H10 V8 Z" />
          <line x1="12" y1="4" x2="12" y2="11" />
          <line x1="4" y1="14" x2="9" y2="14" />
          <Tip x={10} y={12} />
        </Frame>
      );
    case 'width_in_x':
      return (
        <Frame className={className}>
          <rect x="4" y="6" width="4" height="12" />
          <rect x="16" y="6" width="4" height="12" />
          <line x1="9" y1="12" x2="15" y2="12" />
          <Tip x={12} y={12} />
        </Frame>
      );
    case 'width_in_y':
      return (
        <Frame className={className}>
          <rect x="6" y="4" width="12" height="4" />
          <rect x="6" y="16" width="12" height="4" />
          <line x1="12" y1="9" x2="12" y2="15" />
          <Tip x={12} y={12} />
        </Frame>
      );
    case 'width_out_x':
      return (
        <Frame className={className}>
          <rect x="9" y="6" width="6" height="12" />
          <line x1="4" y1="12" x2="8" y2="12" />
          <line x1="20" y1="12" x2="16" y2="12" />
          <Tip x={8} y={12} />
        </Frame>
      );
    case 'width_out_y':
      return (
        <Frame className={className}>
          <rect x="6" y="9" width="12" height="6" />
          <line x1="12" y1="4" x2="12" y2="8" />
          <line x1="12" y1="20" x2="12" y2="16" />
          <Tip x={12} y={8} />
        </Frame>
      );
    case 'dia_in':
      return (
        <Frame className={className}>
          <circle cx="12" cy="12" r="7" />
          <line x1="12" y1="12" x2="18" y2="12" />
          <line x1="12" y1="12" x2="12" y2="6" />
          <line x1="12" y1="12" x2="6" y2="12" />
          <line x1="12" y1="12" x2="12" y2="18" />
          <Tip x={12} y={12} />
        </Frame>
      );
    case 'dia_out':
      return (
        <Frame className={className}>
          <circle cx="12" cy="12" r="5" />
          <line x1="3" y1="12" x2="6" y2="12" />
          <line x1="21" y1="12" x2="18" y2="12" />
          <line x1="12" y1="3" x2="12" y2="6" />
          <line x1="12" y1="21" x2="12" y2="18" />
          <Tip x={6} y={12} />
        </Frame>
      );
    case 'obstacle_dia':
      return (
        <Frame className={className}>
          <circle cx="12" cy="12" r="8" />
          <circle cx="12" cy="12" r="3" />
          <line x1="12" y1="12" x2="19" y2="12" />
          <Tip x={16} y={12} />
        </Frame>
      );
    case 'obstacle_w_x':
      return (
        <Frame className={className}>
          <rect x="3" y="5" width="4" height="14" />
          <rect x="17" y="5" width="4" height="14" />
          <rect x="10" y="9" width="4" height="6" />
          <line x1="8" y1="12" x2="9.5" y2="12" />
          <Tip x={8.5} y={12} />
        </Frame>
      );
    case 'obstacle_w_y':
      return (
        <Frame className={className}>
          <rect x="5" y="3" width="14" height="4" />
          <rect x="5" y="17" width="14" height="4" />
          <rect x="9" y="10" width="6" height="4" />
          <line x1="12" y1="8" x2="12" y2="9.5" />
          <Tip x={12} y={8.5} />
        </Frame>
      );
    case 'three_in':
      return (
        <Frame className={className}>
          <circle cx="12" cy="12" r="7" />
          <Tip x={19} y={12} />
          <Tip x={8.5} y={5.8} />
          <Tip x={8.5} y={18.2} />
        </Frame>
      );
    case 'three_out':
      return (
        <Frame className={className}>
          <circle cx="12" cy="12" r="5" />
          <Tip x={21} y={12} />
          <Tip x={6.5} y={4.5} />
          <Tip x={6.5} y={19.5} />
        </Frame>
      );
    default:
      return (
        <Frame className={className}>
          <rect x="5" y="5" width="14" height="14" />
          <line x1="8" y1="12" x2="16" y2="12" />
        </Frame>
      );
  }
}
