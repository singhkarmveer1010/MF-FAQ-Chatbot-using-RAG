---
name: FinSecure
colors:
  surface: '#f8f9ff'
  surface-dim: '#cbdbf5'
  surface-bright: '#f8f9ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#eff4ff'
  surface-container: '#e5eeff'
  surface-container-high: '#dce9ff'
  surface-container-highest: '#d3e4fe'
  on-surface: '#0b1c30'
  on-surface-variant: '#3c4a43'
  inverse-surface: '#213145'
  inverse-on-surface: '#eaf1ff'
  outline: '#6c7a73'
  outline-variant: '#bbcac1'
  surface-tint: '#006c4f'
  primary: '#006c4f'
  on-primary: '#ffffff'
  primary-container: '#00b386'
  on-primary-container: '#003d2c'
  inverse-primary: '#50ddad'
  secondary: '#0051d5'
  on-secondary: '#ffffff'
  secondary-container: '#316bf3'
  on-secondary-container: '#fefcff'
  tertiary: '#855300'
  on-tertiary: '#ffffff'
  tertiary-container: '#db8c00'
  on-tertiary-container: '#4d2e00'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#71fac8'
  primary-fixed-dim: '#50ddad'
  on-primary-fixed: '#002116'
  on-primary-fixed-variant: '#00513b'
  secondary-fixed: '#dbe1ff'
  secondary-fixed-dim: '#b4c5ff'
  on-secondary-fixed: '#00174b'
  on-secondary-fixed-variant: '#003ea8'
  tertiary-fixed: '#ffddb8'
  tertiary-fixed-dim: '#ffb95f'
  on-tertiary-fixed: '#2a1700'
  on-tertiary-fixed-variant: '#653e00'
  background: '#f8f9ff'
  on-background: '#0b1c30'
  surface-variant: '#d3e4fe'
typography:
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.02em
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.01em
  headline-sm:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-lg:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: 0.01em
  label-md:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.02em
  label-sm:
    fontFamily: Inter
    fontSize: 11px
    fontWeight: '500'
    lineHeight: 16px
    letterSpacing: 0.03em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  2xl: 48px
  3xl: 64px
  container-max: 1200px
  gutter: 24px
  margin-mobile: 16px
  margin-desktop: 32px
---

## Brand & Style
The design system is engineered to project absolute reliability and financial clarity. Targeting modern investors and users seeking a friction-less wealth management experience, the aesthetic balances the precision of an enterprise tool with the approachability of a lifestyle app.

The style is a refined iteration of **Corporate Modernism**, heavily influenced by Material Design 3's structural logic but elevated for a premium fintech context. It utilizes solid surfaces, high-quality typography, and intentional whitespace to reduce cognitive load. Visual hierarchy is established through surface color shifts and subtle tonal layers rather than decorative flourishes. The result is an interface that feels stable, institutional, yet technologically forward.

## Colors
The palette is anchored by "Emerald Green" (#00B386), representing growth and financial health. This is used for primary actions, success states, and positive market movements. "Trust Blue" (#2563EB) serves as the secondary/accent color, reserved for information density, links, and secondary interactive elements to reinforce credibility.

The background uses a "Soft Grey-Blue" (#F7F9FC) to reduce glare and provide a sophisticated canvas for "Pure White" (#FFFFFF) cards. Semantic colors for Warning and Error follow industry standards but are calibrated for high legibility against the light background. Text colors should use a range of Slate grays to ensure accessible contrast ratios while maintaining a premium feel.

## Typography
This design system utilizes **Inter** for all roles to maximize readability across high-density data views and mobile screens. The typographic scale is highly disciplined, prioritizing clear distinctions between data points and descriptive text.

For large monetary displays or primary headings, a tight negative letter-spacing is applied to maintain a cohesive visual block. Labels and captions use slightly increased letter-spacing and medium weights to ensure legibility at small sizes, particularly for secondary financial metadata.

## Layout & Spacing
The layout follows a strict **8px grid system** to ensure mathematical harmony across all components. 

- **Desktop:** A 12-column fluid grid with 24px gutters. Content is typically contained within a 1200px max-width wrapper for dashboard views.
- **Tablet:** 8-column grid with 24px gutters.
- **Mobile:** 4-column grid with 16px side margins.

Horizontal spacing between related data points (e.g., a stock ticker and its price) should use 8px or 12px, while vertical spacing between distinct card sections should utilize 24px or 32px to provide breathing room and emphasize hierarchy.

## Elevation & Depth
Depth is communicated through **Tonal Layers** and extremely soft, diffused shadows. This design system avoids harsh borders in favor of subtle elevation cues that signify interactivity.

1.  **Level 0 (Background):** #F7F9FC — Used for the main canvas.
2.  **Level 1 (Cards/Surfaces):** #FFFFFF — Elevated with a soft shadow (0px 4px 20px rgba(0, 0, 0, 0.04)).
3.  **Level 2 (Overlays/Modals):** #FFFFFF — Elevated with a deeper shadow (0px 10px 40px rgba(0, 0, 0, 0.08)).

Borders are used sparingly, specifically a 1px solid border in #E2E8F0 for input fields or to separate items within a list on a white surface.

## Shapes
The shape language is defined by a "Rounded" philosophy to soften the clinical nature of financial data. 

- **Cards & Primary Containers:** Use a 16px (1rem) radius to create a friendly, modern container.
- **Buttons & Inputs:** Use an 8px (0.5rem) radius to maintain a professional, structured appearance while remaining consistent with the overall softness.
- **Icons & Small UI Elements:** Use a 4px (0.25rem) radius for things like checkboxes or status indicators.

Avoid fully circular "pill" shapes for buttons to maintain the serious "FinTech" character, except for small tags or chips.

## Components

### Buttons
- **Primary:** Solid #00B386 with White text. No gradients. 8px radius.
- **Secondary:** White background with #00B386 border and text.
- **Ghost:** Transparent background with #2563EB text, used for less prominent actions like "Cancel" or "View Details."

### Cards
Cards are the primary structural unit. They must have a white background, 16px corner radius, and a soft 4px-blur shadow. Padding within cards should be a consistent 24px (lg spacing).

### Input Fields
Inputs use a white background with a 1px #E2E8F0 border. On focus, the border transitions to #00B386 with a 2px width. Labels sit above the field in Label-MD styling.

### Chips & Status Indicators
- **Positive Change:** Green background (10% opacity) with #00B386 text.
- **Negative Change:** Red background (10% opacity) with #EF4444 text.
- These use a pill-shape (full round) to distinguish them from actionable buttons.

### Lists
Standard list items use 16px vertical padding with a subtle 1px divider (#F1F5F9). Interaction states should use a soft background fill change to #F7F9FC rather than an outline.