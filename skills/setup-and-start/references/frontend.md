# UI/UX pack — visual design system and verifiable quality

## Before any JSX/CSS
- Identify persona, primary conversion/action, brand tone, language direction and core navigation.
- Select ONE cohesive design system: typography hierarchy, grid/spacing scale, semantic colors, radius, elevations, animation and reusable states.
- Design the difficult states too: error, empty, loading, offline, validation, disabled, destructive action, dense data, long translated text.
- Establish responsive patterns for 390px and 1440px. Prioritize real user journeys, not glossy static landing pages.
- Avoid copy-paste AI defaults: random gradients, endless rounded cards, excessive whitespace, unreadable low-contrast text.

## Implement
- Use semantic HTML, labels, focus states, keyboard support, headings, meaningful alt text and reduced-motion preferences.
- Use existing component system; avoid adding parallel UI libraries without evidence.
- Arabic/RTL: set `lang` and `dir` properly, check mixed digits/Latin/SKU/currency, directional icons and mirrored layouts. Do NOT mirror photos/logos.
- Include mobile and desktop navigation, overlays, form errors, real-data density and skeleton loading.

## Visual Quality Loop — mandatory for visually significant changes
1. Start the actual application in a trusted local preview.
2. If Playwright Python is installed and Chromium provisioned, use:
   `python <skill-root>/scripts/browser_audit.py http://localhost:3000`
   Results and screenshots are stored under `.setup-start/visual-evidence/` (ignored by Git).
3. Observe both screenshots, then check spacing, typography, contrast, alignment, overflow, viewport scaling, real imagery and component consistency. A programmatic smoke PASS does **not** certify attractive design.
4. Test at least one full keyboard journey, form validation, narrow screens and RTL if required.
5. Fix concrete issues, re-run screenshots and compare. Report actual browser failures and anything not inspected.

External inspiration: UI/UX Pro Max, Anthropic frontend-design, Vercel interface guidelines, Google design.md. Link/reference only; do not silently install or relicense external skills.
