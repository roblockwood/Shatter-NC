# Shatter Branding Guide

## Application Name

**Shatter v0.1.0**

CNC Management Platform for Brother CNC Machines

## Icon Design

The Shatter icon is based on a classic CNC machine light tower (stack light), which is a universal symbol in manufacturing for machine status indication.

### Icon Description

The favicon features a stylized 3-light tower with:
- **Red light** (top) - Indicates alarm/error state
- **Yellow light** (middle) - Indicates warning/attention needed
- **Green light** (bottom) - Indicates running/normal operation

### Icon Files

- **SVG**: [frontend/public/favicon.svg](../frontend/public/favicon.svg)
- **Format**: Scalable Vector Graphics (works at any size)
- **Dimensions**: 64x64 viewBox (scales cleanly)

### Color Palette

The icon uses manufacturing-standard light tower colors:

| Light | Color | Hex Code | Usage |
|-------|-------|----------|-------|
| Red | Alert | `#e74c3c` | Machine alarms, errors, offline |
| Yellow | Warning | `#f39c12` | Warnings, attention needed |
| Green | Normal | `#27ae60` | Running, operational, online |
| Tower | Dark Gray | `#444` | Tower body |
| Base | Charcoal | `#333` | Tower base |

### Design Elements

1. **Glow Effect**: Each light has a subtle glow ring (30% opacity) to simulate illumination
2. **Reflections**: Small white circles on lights add depth and realism
3. **Simple Geometry**: Clean shapes for crisp rendering at small sizes
4. **Manufacturing Aesthetic**: Industrial color scheme matches CNC environment

## Browser Tab Display

When the application is open in a browser:
- **Tab Title**: "Shatter v0.1.0"
- **Favicon**: CNC light tower icon

## Future Branding

### Potential Enhancements
- Add PNG versions for broader compatibility (16x16, 32x32, 64x64)
- Create Apple touch icon for mobile bookmarks
- Design a full logo with text for documentation/marketing
- Create dark mode variant of icon

### Version Display
The version number is currently hardcoded in:
- [frontend/index.html](../frontend/index.html) - Browser tab title
- [frontend/package.json](../frontend/package.json) - Package metadata
- [backend/app/core/config.py](../backend/app/core/config.py) - API metadata

Consider centralizing version in a single config file.

## Symbolism

The light tower icon was chosen because:
1. **Universal Recognition**: Instantly recognizable to anyone in manufacturing
2. **Status Indication**: Mirrors the app's purpose (monitoring machine status)
3. **Simple & Scalable**: Works at any size from 16px to full screen
4. **Professional**: Industrial aesthetic matches the target users
5. **Color Coded**: Red/Yellow/Green matches the app's machine status colors

## Usage Guidelines

### Do's ✓
- Use the icon to represent Shatter in documentation
- Maintain the 3-light vertical arrangement
- Keep the color scheme consistent with manufacturing standards
- Scale the SVG (it's resolution-independent)

### Don'ts ✗
- Don't rotate the light tower horizontally
- Don't change the order of colors (red is always top)
- Don't use non-manufacturing colors
- Don't add text to the favicon (too small to read)

## Technical Implementation

```html
<!-- HTML Head -->
<link rel="icon" type="image/svg+xml" href="/favicon.svg" />
<title>Shatter v0.1.0</title>
```

The SVG format ensures:
- Sharp rendering on retina/high-DPI displays
- Small file size (~1KB)
- Fast loading
- No quality loss when scaled
