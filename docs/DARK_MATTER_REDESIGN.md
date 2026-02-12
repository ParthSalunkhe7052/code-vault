# Dark Matter Theme - Complete Redesign

## Overview

This document outlines the complete redesign of the Dark Matter theme implementation, addressing the "weird glow" issue on desktop hover and the "not wrapping wizard" layout problems.

## Problems Fixed

### 1. Weird Glow on Desktop Hover
**Issue**: The global CSS transition on all elements (`*, *::before, *::after`) was applying `box-shadow` transitions to everything, including hover states. This caused a pulsing/washing glow effect on desktop.

**Root Cause**:
```css
/* OLD - CAUSES PROBLEM */
*, *::before, *::after {
    transition: background-color 300ms ease,
                border-color 300ms ease,
                box-shadow 300ms ease; /* Applied to ALL hover states */
}
```

**Solution**:
- Removed global transitions from all elements
- Added selective transitions only on the `html` element for theme switching
- Added targeted transitions per-component (buttons, cards, nav items)
- Used `@media (hover: hover)` to only apply hover effects on desktop devices

### 2. Text Wrapping in Dark Matter Mode
**Issue**: The previous implementation applied `font-family: monospace` to ALL text in Dark Matter mode, which:
- Broke layout spacing
- Caused text overflow in narrow containers
- Made wizards and forms look broken

**Root Cause**:
```css
/* OLD - BREAKS LAYOUT */
.dark-matter body,
.dark-matter {
    font-family: 'Geist Mono', 'JetBrains Mono', ui-monospace, monospace;
}
```

**Solution**:
- Only apply monospace font to code blocks and explicit mono classes
- Keep sans-serif for UI text (headers, labels, paragraphs)
- Add subtle letter-spacing to headings for the "hacker" feel without breaking layouts

```css
/* NEW - PROPER LAYOUT */
.dark-matter code,
.dark-matter pre,
.dark-matter .font-mono,
.dark-matter .mono {
    font-family: 'Geist Mono', 'JetBrains Mono', ui-monospace, monospace;
}

.dark-matter h1, .dark-matter h2, .dark-matter h3, .dark-matter h4 {
    letter-spacing: 0.02em; /* Subtle hacker aesthetic */
}
```

## Files Changed

### 1. `src/index.css`

#### Changes Made:
1. **Removed Global Transitions** (lines 145-153)
   - Old: `*, *::before, *::after { transition: ... }`
   - New: Only `html` gets theme switching transitions

2. **Updated Dark Matter Font Rules** (lines 174-191)
   - Added selective monospace application
   - Added letter-spacing for headings

3. **Clean Glass Card Hover** (lines 254-277)
   - Removed `0 0 0 1px var(--cv-primary-glow)` (main cause of weird glow)
   - Added `transform: translateY(-2px)` for subtle lift
   - Added touch device support (`@media (hover: none)`)

4. **Refined Button Styles** (lines 279-374)
   - Desktop-only hover effects
   - Touch device support
   - Cleaner box-shadows (no pulsing)

5. **Updated Glow Effects** (lines 441-457)
   - Reduced intensity (from 20px/40px to 12px/24px)
   - Added subtle `-2px` spread for cleaner look
   - Added `.glow-strong` for special cases

6. **Dark Matter Specific Styles** (lines 476-519)
   - `.dm-brand-accent` - Gradient text for branding
   - `.dm-scanline-bg` - Optional subtle scanline effect
   - `.dm-border-accent` - Coral border theme
   - Code block styling

### 2. `src/components/ThemeToggle.jsx`

**Completely Redesigned**:
- Clean, minimal design
- Clear labels showing current theme
- No hover glow issues
- Theme-aware styling

**Visual Changes**:
```
OLD: [🌙] Dark ---- [✨] Matter
     Weird pulsing glow on switch

NEW: [Default] [O---●] [Matter]
     Clean, labeled, no weird effects
```

### 3. `src/contexts/SettingsContext.jsx`

**Minor Improvements**:
- Added localStorage wrapper with error handling
- Cleaner theme application
- Removed unused 'dark' class handling

### 4. `src/components/Layout.jsx`

**Updated Navigation Items**:
- Removed `hover:translate-x-1` (was causing layout shifts)
- Removed `transition-all duration-200` from nav items
- Added inline style for controlled transitions
- Cleaner hover backgrounds using `var(--cv-border-subtle)`

**Before**:
```jsx
className="... hover:bg-white/5 hover:border-white/5 hover:translate-x-1 transition-all duration-200"
```

**After**:
```jsx
className="... hover:bg-[var(--cv-border-subtle)] hover:border-[var(--cv-border)]"
style={{ transition: 'all 0.15s cubic-bezier(0.4, 0, 0.2, 1)' }}
```

## Theme-Specific Features

### Dark Matter Theme

The Dark Matter theme now provides:

1. **Colors**: Warm coral/orange accent (hsl 22.3°, 75.51%, 61.57%)
2. **Backgrounds**: Purple-tinged dark (hsl 270°, 5.56%, 7.06%)
3. **Fonts**: Sans-serif for UI, monospace for code
4. **Effects**: Subtle scanlines, coral borders, gradient text accents
5. **No Breaking Changes**: All wizards, forms, and layouts work properly

### Default Dark Theme

Remains unchanged in functionality but benefits from:
- No global transitions (better performance)
- Cleaner hover states
- Better mobile support

## Testing Checklist

- [x] Default theme hover states work correctly
- [x] Dark Matter theme hover states work correctly
- [x] No weird glow on desktop hover
- [x] Wizard layouts wrap text properly
- [x] Forms display correctly in both themes
- [x] Navigation items work properly
- [x] Buttons have clean hover states
- [x] Theme toggle works and saves to localStorage
- [x] Mobile devices don't show hover effects
- [x] Cards lift subtly on hover (desktop only)

## Performance Notes

**Improvements**:
- Removed global `*` transition (better performance)
- Selective transitions reduce CSS overhead
- Mobile devices skip hover animations

**Trade-offs**:
- Theme switching now only transitions `html` element colors
- Individual components define their own transitions
- Slightly more CSS, but better targeted

## Migration Guide

If you're using these components:

### For New Components:
```jsx
// Use the new button classes
<button className="btn-primary">Click</button>

// Use the new glass-card with proper hover
<div className="glass-card">Content</div>

// For custom hover needs, use desktop-only media query
@media (hover: hover) and (pointer: fine) {
    .my-component:hover {
        transform: translateY(-1px);
    }
}
```

### For Existing Code:
- Remove any `hover:translate-x-1` or `hover:-translate-y-1` from flex containers
- Replace `hover:bg-white/5 hover:border-white/5` with theme-aware classes
- Remove `transition-all duration-200` on parent elements, add to children if needed

## Summary

The Dark Matter theme is now a **complete, working redesign** that:
1. ✅ Fixes the "weird glow" issue
2. ✅ Allows proper text wrapping in wizards
3. ✅ Maintains the hacker aesthetic
4. ✅ Works on desktop and mobile
5. ✅ Has clean, modern interactions
6. ✅ Uses theme-aware styling throughout
