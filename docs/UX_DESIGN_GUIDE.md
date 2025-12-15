# Shatter - UX Design Guide

## Design Philosophy: Mod-Retro Terminal

**Core Aesthetic:** Modern MS-DOS/terminal interface with ASCII art, monospace fonts, and CRT-inspired visuals.

**Key Principles:**
- Dark mode only (no light theme)
- Monospace typography throughout
- ASCII art for graphics, progress bars, and UI elements
- **NO EMOJI** - Use ASCII characters only (/, -, |, *, etc.) to maintain terminal aesthetic
- CRT/terminal visual effects (optional scanlines, glow)
- Command-line inspired interactions
- Information density - pack data like a terminal
- Green/amber phosphor color schemes with modern accents

---

## Color Palette

### Primary Colors (CRT Phosphor-Inspired)

```
Background:     #0a0a0a (near black)
Surface:        #1a1a1a (dark gray)
Border:         #2a2a2a (medium gray)

Primary Text:   #00ff00 (classic green phosphor)
Secondary Text: #33ff33 (lighter green)
Muted Text:     #66ff66 (dimmed green)

Accent 1:       #ffaa00 (amber/warning)
Accent 2:       #00ffff (cyan/info)
Error:          #ff0000 (red)
Success:        #00ff00 (green)
Warning:        #ffaa00 (amber)
```

### Alternative Schemes
Users could switch between phosphor colors:
- **Green Phosphor** (default): `#00ff00`
- **Amber Phosphor**: `#ffb000`
- **White Phosphor**: `#f0f0f0`
- **Cyan Phosphor**: `#00ffff`

---

## Typography

### Fonts (in order of preference)
1. **IBM Plex Mono** - Free, excellent readability
2. **JetBrains Mono** - Modern, ligatures
3. **Fira Code** - Clean, widely used
4. **Courier New** - Fallback
5. **monospace** - System fallback

### Font Sizes
```css
--font-xs: 10px;   /* Metadata, timestamps */
--font-sm: 12px;   /* Secondary text, labels */
--font-md: 14px;   /* Body text, data */
--font-lg: 16px;   /* Headings, emphasis */
--font-xl: 20px;   /* Large headers */
--font-xxl: 24px;  /* ASCII art titles */
```

### Text Styles
```css
.terminal-text {
  font-family: 'IBM Plex Mono', monospace;
  letter-spacing: 0.05em;
  text-transform: none; /* Preserve case for code */
}

.terminal-header {
  text-transform: uppercase;
  font-weight: 700;
}

.terminal-glow {
  text-shadow: 0 0 8px currentColor;
}
```

---

## Layout Patterns

### Terminal Window Structure
```
┌─────────────────────────────────────────────────────────────┐
│ SHATTER v0.1.0 │ MACHINE MONITOR │ [CONNECTION: ●●●●○ 4/5]  │ ← Status bar
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────┐  │
│  │   SPEEDIO      │  │   SPEEDIO-02   │  │  SPEEDIO-03  │  │ ← Machine cards
│  │   [RUNNING]    │  │   [IDLE]       │  │  [OFFLINE]   │  │
│  │   ████████░░   │  │   ──────────   │  │   ░░░░░░░░░░ │  │ ← ASCII progress
│  │   O2045.NC     │  │   IDLE         │  │   ERROR 404  │  │
│  │   45/100 pcs   │  │   0/0 pcs      │  │   ───────    │  │
│  └────────────────┘  └────────────────┘  └──────────────┘  │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│ > STATUS: 3 MACHINES │ 1 RUNNING │ 1 IDLE │ 1 OFFLINE      │ ← Command line
└─────────────────────────────────────────────────────────────┘
```

### Box Drawing Characters
```
Corners:  ┌ ┐ └ ┘
Lines:    ─ │ ├ ┤ ┬ ┴ ┼
Double:   ═ ║ ╔ ╗ ╚ ╝ ╠ ╣ ╦ ╩ ╬
Rounded:  ╭ ╮ ╰ ╯
```

---

## Component Library

### 1. ASCII Progress Bars

**Horizontal Bar (10-char wide):**
```
  0%: ──────────  or  ░░░░░░░░░░
 25%: ██▌───────  or  ████▌░░░░░
 50%: █████─────  or  █████░░░░░
 75%: ███████▌──  or  ███████▌░░
100%: ██████████  or  ██████████
```

**Vertical Bar:**
```
│█│   100%
│█│    75%
│█│    50%
│▌│    25%
│░│     0%
```

**Spinner (loading):**
```
Frame 1: [/]
Frame 2: [─]
Frame 3: [\]
Frame 4: [│]
```

### 2. Status Indicators

**Connection Status:**
```
ONLINE:   ● [#00ff00]
OFFLINE:  ○ [#ff0000]
WARNING:  ◐ [#ffaa00]
UNKNOWN:  ◌ [#666666]
```

**Machine State:**
```
[RUNNING]    - Green background
[IDLE]       - Cyan background
[ERROR]      - Red background
[OFFLINE]    - Gray/dimmed
[ALARM]      - Blinking red
```

### 3. Machine Cards

```
┌─────────────────────────┐
│ SPEEDIO-01       [RUN] ●│
├─────────────────────────┤
│ O2045.NC               │
│ BRACKET_V2             │
│                        │
│ CYCLE:  ████████░░ 78% │
│ TIME:   00:05:32       │
│ PARTS:  045/100        │
│                        │
│ X: +123.456  FEED: 850 │
│ Y: -078.901  RPM: 8000 │
│ Z: +025.000            │
└─────────────────────────┘
```

### 4. Alarm/Error Display

```
┌────────────────────────────────────────┐
│ !!! ALARM - MACHINE 02 !!!            │
├────────────────────────────────────────┤
│ CODE:     P-041                       │
│ MESSAGE:  SPINDLE OVERLOAD            │
│ TIME:     2024-12-01 03:45:12         │
│ ACTION:   ► RESET REQUIRED            │
└────────────────────────────────────────┘
```

### 5. Data Tables

```
┌────┬──────────────┬──────────┬─────────┬────────┐
│ ID │ PROGRAM      │ STATUS   │ TIME    │ PARTS  │
├────┼──────────────┼──────────┼─────────┼────────┤
│ 01 │ O2045.NC     │ RUNNING  │ 0:05:32 │ 45/100 │
│ 02 │ O3012.NC     │ IDLE     │ ──────  │ ────── │
│ 03 │ OFFLINE      │ OFFLINE  │ ──────  │ ────── │
└────┴──────────────┴──────────┴─────────┴────────┘
```

### 6. ASCII Charts

**Bar Chart (Parts per Day):**
```
 MON │████████████████          160
 TUE │██████████████            140
 WED │████████████████████      200
 THU │██████████                100
 FRI │██████████████████        180
     └─────────────────────────────
       0   50  100  150  200  250
```

**Line Chart (Cycle Time Trend):**
```
 10m │     ╭─╮
  8m │    ╭╯ ╰╮
  6m │   ╭╯   ╰╮
  4m │  ╭╯     ╰╮
  2m │ ╭╯       ╰─
     └──────────────
       1  2  3  4  5
```

**Oscilloscope Display (Status Timeline):**
```
OPERATING │●───────────────────────────────●───────────────
STANDBY   │     ╱╲                          │
STOPPED   │    ╱  ╲                         │
ERROR     │   ╱    ╲                        │
OFF       │  ╱      ╲───────────────────────●
          └────────────────────────────────────
          PAST                              NOW
```

**Oscilloscope Component - Detailed Specification:**

The oscilloscope is a **smooth, analog-style visualization** that breaks from the strict terminal aesthetic to provide a more fluid representation of machine status over time. It uses SVG rendering for smooth curves and transitions, while maintaining the terminal color scheme and layout structure.

**Visual Design:**
- **Y-axis**: Status levels mapped to vertical positions
  - Status order (top to bottom): `OPERATING`, `STANDBY`, `STOPPED`, `ERROR`, `OFF`
  - Each status occupies a horizontal "row" or band
  - Status labels displayed on the left side of the graph
- **X-axis**: Time span (configurable via time range selector)
  - Available ranges: `1H` (1 hour), `8H` (8 hours), `24H` (24 hours), `7D` (7 days)
  - "PAST" marker on the left, "NOW" marker on the right
  - Time division markers at logical intervals (e.g., 15m for 1H, 1h for 8H)
- **Trace Line**: Smooth SVG path connecting status transitions
  - Uses quadratic bezier curves for smooth transitions between status levels
  - Subtle sine-based oscillation within each status row for analog feel
  - Thin stroke width (0.8px) with subtle glow animation
  - Color: Primary green (`#00ff00`) with slight width variation (15% intensity)
- **Timestamp Indicators**: Vertical dashed lines at data points
  - Thin, subtle lines (`strokeWidth: 0.5`, `opacity: 0.25`)
  - Dashed pattern (`strokeDasharray: "3 2"`)
  - Hover tooltips show status and timestamp
  - Invisible hover areas (0.5% width) for easier interaction
- **Time Division Lines**: Additional vertical markers for time reference
  - Subtle lines (`opacity: 0.2`, `strokeDasharray: "1 1"`)
  - Positioned at logical intervals based on time range
  - Labels displayed in bottom axis section
- **Background**: Dark surface color (`var(--color-bg-surface)`)
- **Padding**: 8px top/bottom to prevent trace overflow

**Implementation Details:**
- **Technology**: SVG-based rendering (not ASCII)
- **Smooth Transitions**: Quadratic bezier curves between status points
- **Oscillation**: Subtle sine wave within status rows (frequency: 2.5, amplitude: 12% of row height)
- **Scaling**: Dynamic horizontal scaling using CSS `transform: scaleX()` to fit container width
- **Responsive**: Uses `ResizeObserver` to recalculate width on container resize
- **Real-time Updates**: Integrates with WebSocket for live status changes
- **Current Status**: Always shows the most recent status from machine polling

**Status Mapping:**
The component normalizes machine status strings to standard values:
- `operating`, `running` → `OPERATING`
- `standby`, `idle` → `STANDBY`
- `stopped` → `STOPPED`
- `error`, `error occurred` → `ERROR`
- `off`, `offline` → `OFF`

**Usage Guidelines:**
- **Primary Use**: Machine detail view status timeline pane
- **Hover Behavior**: Shows tooltip with status and timestamp at data points
- **Click Behavior**: Does not expand (content always fits within pane)
- **Time Range Selection**: User can switch between 1H, 8H, 24H, 7D via buttons
- **Data Source**: Fetches from `/api/machines/{machine_id}/status-history` endpoint
- **Update Frequency**: Refreshes when time range changes or on component mount

**Component Props:**
```typescript
interface StatusTimelineProps {
  machineId: number;
  currentStatus?: string;  // Current machine status from WebSocket
  isOnline?: boolean;       // Whether machine is online
  onExpand?: () => void;   // Optional expand callback (not used currently)
}
```

**CSS Classes:**
- `.status-timeline` - Main container
- `.oscilloscope-display` - SVG container
- `.oscilloscope-svg` - SVG element
- `.oscilloscope-trace` - Main path element
- `.oscilloscope-timestamp-line` - Vertical timestamp indicators
- `.oscilloscope-time-division-line` - Time division markers
- `.oscilloscope-tooltip` - Hover tooltip
- `.oscilloscope-x-axis` - Bottom axis with labels

**Accessibility:**
- Tooltips provide status and timestamp information on hover
- Time range buttons are keyboard accessible
- Status labels are clearly visible on the left side
- Color is not the only indicator (status labels provide context)

**Note on Aesthetic Exception:**
This is the **only component** that breaks from the strict ASCII/terminal aesthetic. The smooth SVG rendering provides a more analog, oscilloscope-like feel that enhances the visualization of status transitions over time. All other components maintain the ASCII/box-drawing character aesthetic.

---

## Screen Layouts

### Main Dashboard

```
╔═══════════════════════════════════════════════════════════════════════╗
║ SHATTER v0.1.0                        [SYS] [NET] [LOG]    03:45:12  ║
╠═══════════════════════════════════════════════════════════════════════╣
║                                                                        ║
║  ┌─ FLEET OVERVIEW ────────────────────────────────────────────────┐  ║
║  │ MACHINES: 5  │  RUNNING: 3  │  IDLE: 1  │  OFFLINE: 1          │  ║
║  │ PARTS/HR: 24 │  UPTIME: 87% │  ALARMS: 0                       │  ║
║  └──────────────────────────────────────────────────────────────────┘  ║
║                                                                        ║
║  ┌─ MACHINE 01: SPEEDIO ─┐  ┌─ MACHINE 02: SPEEDIO ─┐               ║
║  │ ● RUNNING              │  │ ○ OFFLINE              │               ║
║  │                        │  │                        │               ║
║  │ PROG:  O2045.NC        │  │ PROG:  ────────        │               ║
║  │ CYCLE: ████████░░  78% │  │ STATUS: CONN LOST      │               ║
║  │ TIME:  00:05:32        │  │ LAST:   5 min ago      │               ║
║  │ PARTS: 045/100         │  │                        │               ║
║  │                        │  │                        │               ║
║  │ X: +123.456   F: 850   │  │ ERROR: 404             │               ║
║  │ Y: -078.901   S: 8000  │  │                        │               ║
║  │ Z: +025.000            │  │                        │               ║
║  └────────────────────────┘  └────────────────────────┘               ║
║                                                                        ║
╠═══════════════════════════════════════════════════════════════════════╣
║ > _                                                                    ║
╚═══════════════════════════════════════════════════════════════════════╝
```

### Machine Detail View

```
╔═══════════════════════════════════════════════════════════════════════╗
║ [←] SPEEDIO-01                                          03:45:12 [X] ║
╠═══════════════════════════════════════════════════════════════════════╣
║                                                                        ║
║  ┌─ CURRENT STATUS ──────────────────────────────────────────────┐    ║
║  │ STATE:    [RUNNING] ●                                         │    ║
║  │ PROGRAM:  O2045.NC (BRACKET_V2)                               │    ║
║  │ CYCLE:    ████████████░░░░░░░░ 67% │ 00:05:32 / 00:08:15     │    ║
║  │ PARTS:    045/100                                             │    ║
║  └───────────────────────────────────────────────────────────────┘    ║
║                                                                        ║
║  ┌─ POSITION ──────────┐  ┌─ MOTION ─────────────────────────────┐   ║
║  │ X:  +123.456 mm     │  │ FEED:    850 mm/min                  │   ║
║  │ Y:  -078.901 mm     │  │ RAPID:   15000 mm/min                │   ║
║  │ Z:  +025.000 mm     │  │ SPINDLE: 8000 rpm                    │   ║
║  │ A:  +000.000 deg    │  │                                      │   ║
║  └─────────────────────┘  └──────────────────────────────────────┘   ║
║                                                                        ║
║  ┌─ TOOLS ───────────────────────────────────────────────────────┐   ║
║  │ #01  1/4 END MILL     D: 6.35mm   L: 50mm    [SPINDLE]       │   ║
║  │ #02  1/8 BALL MILL    D: 3.18mm   L: 38mm                     │   ║
║  │ #03  SPOT DRILL       D: 6.00mm   L: 45mm                     │   ║
║  └───────────────────────────────────────────────────────────────┘   ║
║                                                                        ║
║  ┌─ ALARMS (0) ───────────────────────────────────────────────────┐  ║
║  │ NO ACTIVE ALARMS                                               │  ║
║  └────────────────────────────────────────────────────────────────┘  ║
║                                                                        ║
╠═══════════════════════════════════════════════════════════════════════╣
║ > COMMANDS: [F]iles [H]istory [T]ools [L]ogs [R]efresh [Q]uit        ║
╚═══════════════════════════════════════════════════════════════════════╝
```

### File Browser

```
╔═══════════════════════════════════════════════════════════════════════╗
║ FILE MANAGER │ SPEEDIO-01                              [UPLOAD] [X]  ║
╠═══════════════════════════════════════════════════════════════════════╣
║                                                                        ║
║  ┌─ NC PROGRAMS (/CNC_MEM/) ─────────────────────────────────────┐   ║
║  │                                                                │   ║
║  │  O-NUM   NAME              SIZE      MODIFIED        STATUS   │   ║
║  │  ─────────────────────────────────────────────────────────────│   ║
║  │  O2045   BRACKET_V2.NC    12.4K    2024-12-01 08:30  [RUN]   │   ║
║  │  O2046   PLATE_REV3.NC     8.2K    2024-11-30 14:22          │   ║
║  │  O2050   TEST_PART.NC      3.1K    2024-11-29 09:15          │   ║
║  │  O3012   FIXTURE_A.NC     15.8K    2024-11-28 16:45          │   ║
║  │  O9999   PROBE_CYCLE.NC    1.2K    2024-11-15 11:00          │   ║
║  │                                                                │   ║
║  │  5 PROGRAMS │ TOTAL: 40.7K │ FREE: 512K                       │   ║
║  │                                                                │   ║
║  └────────────────────────────────────────────────────────────────┘   ║
║                                                                        ║
║  ┌─ SELECTED: O2045 (BRACKET_V2.NC) ─────────────────────────────┐   ║
║  │                                                                │   ║
║  │ TOOLS:     5 (T01, T02, T03, T05, T07)                        │   ║
║  │ RUNTIME:   ~8 min 15 sec                                      │   ║
║  │ STOCK:     150 x 100 x 25 mm                                  │   ║
║  │ WCS:       G54                                                │   ║
║  │ POSTED:    2024-12-01 08:30                                   │   ║
║  │                                                                │   ║
║  │ [DOWNLOAD] [DELETE] [VIEW CODE] [VALIDATE]                    │   ║
║  │                                                                │   ║
║  └────────────────────────────────────────────────────────────────┘   ║
║                                                                        ║
╠═══════════════════════════════════════════════════════════════════════╣
║ > UPLOAD NEW FILE: [DRAG & DROP] or [BROWSE]                         ║
╚═══════════════════════════════════════════════════════════════════════╝
```

---

## Interactive Elements

### Buttons

```css
/* Primary Button */
[ UPLOAD FILE ]    ← Green border, hover: filled green
[ > EXECUTE ]      ← With caret/arrow prefix

/* Secondary Button */
[ CANCEL ]         ← Gray border
[ BACK ]

/* Danger Button */
[ DELETE ]         ← Red border
[ ! STOP ]         ← With warning prefix

/* Icon Buttons */
[↻] REFRESH
[✕] CLOSE
[⚙] SETTINGS
```

### Input Fields

```
> SEARCH: _________________ [↵]
> FILTER: [_____________]

┌─ NEW MACHINE ────────────┐
│ NAME:    [____________] │
│ IP ADDR: [___.___.___.__│
│ FTP USER:[____________] │
│ FTP PASS:[************] │
│                          │
│    [CANCEL]  [CONNECT]  │
└──────────────────────────┘
```

### Dropdown/Select

```
MACHINE: [ SPEEDIO-01 ▼ ]

When open:
┌─────────────────┐
│ > SPEEDIO-01    │
│   SPEEDIO-02    │
│   SPEEDIO-03    │
│   ALL MACHINES  │
└─────────────────┘
```

---

## Animations & Effects

### CRT Effects (Optional - Toggle)

```css
/* Scanlines */
.terminal::before {
  background: repeating-linear-gradient(
    0deg,
    rgba(0, 0, 0, 0.1),
    rgba(0, 0, 0, 0.1) 1px,
    transparent 1px,
    transparent 2px
  );
}

/* Glow */
.terminal-text {
  text-shadow: 0 0 8px currentColor;
}

/* Flicker (subtle) */
@keyframes flicker {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.97; }
}
```

### Loading States

```
LOADING: [/]  →  [─]  →  [\]  →  [│]  (rotate)

CONNECTING TO MACHINE...
[████████████████░░░░░░░░] 67%

UPLOADING O2045.NC...
████████████████████████████████░░░░░░░░░░ 78% | 125KB/160KB
```

### Real-time Updates

```
/* Blinking cursor */
> _  (blinks every 500ms)

/* Live data updates - subtle flash */
PARTS: 045/100  → flash green briefly when incremented

/* Status change - slide in notification */
┌──────────────────────────────┐
│ ✓ SPEEDIO-01 CYCLE COMPLETE │
└──────────────────────────────┘
```

---

## Sound Design (Optional)

**Terminal sounds:**
- Keystroke: Soft mechanical click
- Button click: Terminal beep
- Error: Classic DOS error beep
- Success: Satisfying blip
- Alarm: Urgent beep pattern

**Mute by default, toggle in settings**

---

## Responsive Breakpoints

```
Desktop (>1200px):  3-4 machine cards wide
Tablet (768-1200):  2 machine cards wide
Mobile (<768px):    1 machine card, stack vertically
                    Simplify ASCII art for small screens
```

---

## Accessibility Considerations

Despite retro aesthetic:
- Maintain WCAG contrast ratios (green on black = ~15:1)
- Keyboard navigation for all functions
- Screen reader labels (hidden from visual)
- Option to disable animations/effects
- Font size controls

---

## Tech Stack Recommendations

### Framework
- **React** with TypeScript
- **Vite** for fast builds

### Libraries
```json
{
  "react": "^18.x",
  "typescript": "^5.x",
  "@tanstack/react-query": "^5.x",    // Data fetching
  "zustand": "^4.x",                   // State management
  "react-router-dom": "^6.x",          // Routing
  "framer-motion": "^10.x",            // Animations (optional)
  "ascii-progress": "^2.x",            // ASCII progress bars
  "blessed": "^0.1.x",                 // Terminal UI components
  "xterm": "^5.x"                      // Terminal emulator (if needed)
}
```

### CSS Approach
- **CSS Modules** or **Styled Components**
- CSS custom properties for theming
- No UI framework (build custom components for full control)

---

## Implementation Priority

### Phase 1: Core Visual Language
1. Set up color system & typography
2. Box drawing character components
3. ASCII progress bar component
4. Status indicator components

### Phase 2: Layout Components
1. Terminal window wrapper
2. Machine card component
3. Data table component
4. Navigation/command bar

### Phase 3: Views
1. Main dashboard (machine grid)
2. Machine detail view
3. File browser
4. Settings/system view

### Phase 4: Polish
1. CRT effects toggle
2. Animations & transitions
3. Loading states
4. Error handling UI
5. Keyboard shortcuts

---

## Example Component Patterns

### React Component Structure

```tsx
// MachineCard.tsx
interface MachineCardProps {
  machine: Machine;
  status: MachineStatus;
}

export const MachineCard: React.FC<MachineCardProps> = ({ machine, status }) => {
  return (
    <div className="terminal-box">
      <div className="terminal-box-header">
        {machine.name} {status.isOnline ? '●' : '○'}
      </div>
      <div className="terminal-box-content">
        <div>PROG: {status.program || '──────'}</div>
        <div>
          CYCLE: <ProgressBar value={status.progress} />
        </div>
        <div>PARTS: {status.parts}/{status.target}</div>
      </div>
    </div>
  );
};
```

---

## ASCII Art Assets

### Logo
```
 ███████╗██╗  ██╗ █████╗ ████████╗████████╗███████╗██████╗
 ██╔════╝██║  ██║██╔══██╗╚══██╔══╝╚══██╔══╝██╔════╝██╔══██╗
 ███████╗███████║███████║   ██║      ██║   █████╗  ██████╔╝
 ╚════██║██╔══██║██╔══██║   ██║      ██║   ██╔══╝  ██╔══██╗
 ███████║██║  ██║██║  ██║   ██║      ██║   ███████╗██║  ██║
 ╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝      ╚═╝   ╚══════╝╚═╝  ╚═╝
```

### Machine Status Icons
```
RUNNING:  ►  or  ⚙  or  ▶
STOPPED:  ■  or  ◼  or  ⏹
ERROR:    ✕  or  ⚠  or  !!
IDLE:     ○  or  ─  or  ··
```

---

This design system provides a unique, memorable identity while maintaining modern usability standards. The retro-terminal aesthetic differentiates Shatter from typical industrial dashboards while being highly functional for CNC monitoring.
