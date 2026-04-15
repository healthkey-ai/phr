# HealthKey Patient App — Design Document

**Branch:** patient-app
**Date:** April 2026
**References:** `docs/patient-app-requirements.md`, `docs/patient-app-architecture.md`, `Allen_claude_prototype` (UX reference), `cancerbot/ui.v2` (design system)

> This document is the **visual and interaction contract** for the patient app. It defines the design system, screen-by-screen wireframes, interaction states, user journey, responsive specs, and accessibility requirements. The implementer reads this to know exactly what to build at the pixel level. Where this document conflicts with text in the requirements doc, this document wins for visual/interaction decisions; the requirements doc wins for functional decisions.

---

## Contents

1. [Design Principles](#1-design-principles)
2. [Design System](#2-design-system)
3. [Information Architecture](#3-information-architecture)
4. [Component Library](#4-component-library)
5. [Screen Inventory & Wireframes](#5-screen-inventory--wireframes)
6. [Interaction State Coverage](#6-interaction-state-coverage)
7. [User Journey & Emotional Arc](#7-user-journey--emotional-arc)
8. [Responsive Behavior](#8-responsive-behavior)
9. [Accessibility Specifications](#9-accessibility-specifications)
10. [Microcopy Guidelines](#10-microcopy-guidelines)
11. [Motion & Animation](#11-motion--animation)
12. [Anti-Patterns to Avoid](#12-anti-patterns-to-avoid)

---

## 1. Design Principles

The patient app holds health records for people who are often **anxious, recently diagnosed, post-surgery, elderly, or caring for a sick family member**. Every design decision is calibrated against that user state.

### Core principles

1. **Calm before clever.** When the user is stressed, novelty hurts. Boring patterns are healing patterns. No animations for animation's sake.
2. **Plain language always.** Never display "ECOG performance status 0–4" without "your activity level". Never show "FHIR R4 bundle" to a patient. Clinical codes have plain-language explanations attached.
3. **Trust at the pixel level.** A health record app earns trust through restraint. No marketing flourishes. No emoji confetti on save. The user is not celebrating their cancer diagnosis.
4. **Skip is a first-class action.** Every onboarding step has "Skip for now" with equal visual weight to "Continue." Drop-off is the enemy.
5. **Show provenance.** Every data point shows where it came from (Epic, manual entry, AI extraction with confidence) and when. Trust is earned by being honest about uncertainty.
6. **Recovery over prevention.** Assume people will close the app mid-flow. Every screen is resumable. Auto-save is invisible.
7. **One job per screen.** No screen tries to do two things. The Records tab is for browsing records, not editing them. Editing happens in dedicated forms.
8. **Subtraction default.** If a UI element doesn't earn its pixels, cut it. The patient came here to find their lab results, not admire your design system.
9. **Accessibility is a baseline, not a feature.** WCAG 2.1 AA minimum, AAA where viable. Touch targets ≥ 44px. Color contrast ≥ 4.5:1 for body text.
10. **Mobile-first, not mobile-only.** 70% of healthcare app sessions happen on phones. Design at 375px first, expand from there.

### Anti-patterns (forbidden)

- Generic SaaS hero with "Welcome to HealthKey, your all-in-one health companion"
- 3-column feature grids with icons in colored circles
- Purple/violet gradients
- Decorative blobs, wavy SVG dividers
- Emoji as design elements ("🚀 Boost your health!")
- Centered everything
- Cookie-cutter card mosaic dashboards
- Marketing language inside the app ("Unlock the power of...")
- Modal dialogs as a primary navigation pattern

---

## 2. Design System

### 2.1 Foundation

Inherits from `cancerbot/ui.v2` design tokens (`client/global.css`, `tailwind.config.ts`). All values are HSL CSS custom properties with full light/dark theme support.

### 2.2 Typography

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         TYPOGRAPHY SCALE                                    │
│                                                                             │
│  Family:    Manrope (400, 500, 600, 700, 800)                              │
│  Fallback:  -apple-system, Roboto, Helvetica, sans-serif                   │
│                                                                             │
│  display      48px / 56px / 800   →  Onboarding welcome only                │
│  h1           32px / 40px / 700   →  Page titles                            │
│  h2           24px / 32px / 700   →  Section headings                       │
│  h3           20px / 28px / 600   →  Card titles                            │
│  h4           18px / 24px / 600   →  Subsection labels                      │
│  body-lg      16px / 24px / 500   →  Default body                           │
│  body         14px / 20px / 500   →  Form labels, secondary text            │
│  body-sm      13px / 18px / 500   →  Captions, metadata                     │
│  caption      12px / 16px / 500   →  Timestamps, fine print                 │
│  button       14px / 20px / 600   →  All buttons                            │
│  mono         13px / 20px / 500   →  Lab values, codes                      │
│                                                                             │
│  Line-length: max 65 characters for body text (a11y best practice)          │
│  Letter-spacing: -0.01em for h1/h2 (display only); 0 for body              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.3 Color Tokens

> See `docs/patient-app-requirements.md` §10 for the full HSL value table. This section defines **semantic intent**, not raw values.

**Backgrounds**
- `bg-app` — main page background (white in light, near-black in dark)
- `bg-surface` — cards, panels, elevated surfaces
- `bg-muted` — input backgrounds, hover states
- `bg-overlay` — modal backdrop (rgba(0,0,0,0.6))

**Text**
- `text-primary` — body copy (highest contrast)
- `text-secondary` — supporting text, descriptions
- `text-tertiary` — placeholder, metadata
- `text-disabled` — disabled state
- `text-brand` — links and brand-coloured labels
- `text-on-brand` — text on brand-coloured backgrounds

**Brand**
- `brand-50` / `brand-100` / `brand-200` — backgrounds for badges, banners
- `brand-500` / `brand-600` / `brand-700` — primary actions, links, focus rings
- HealthKey primary: deep blue `hsl(212, 87%, 33%)`
- Cyan accent (sparingly): `hsl(199, 100%, 64%)`

**Status colors** (used for clinical signal, not decoration)
- `success` — completed, in-range, verified, synced
- `warning` — out-of-range, attention needed, expiring soon
- `error` — failed sync, allergy alert, expired grant
- `info` — neutral notice, "did you know"

**Cancer accent** (used only on disease-profile screens, never elsewhere)
- `cancer-50` / `cancer-700` — rose/red tint
- Visually distinguishes oncology fields from general health fields

### 2.4 Spacing Scale

```
0    →  0px        no space
1    →  4px        tightest (icon padding, border-radius for chips)
2    →  8px        related items (label + input)
3    →  12px       form-field internal padding
4    →  16px       default gap, paragraph spacing
5    →  20px       between related groups
6    →  24px       section internal padding
8    →  32px       between sections
10   →  40px       page margin (mobile)
12   →  48px       between major page regions
16   →  64px       page top/bottom padding (desktop)
20   →  80px       hero / empty state vertical breathing room
```

Based on a 4px grid. Always use spacing tokens, never hard-coded pixels.

### 2.5 Border Radius

```
none   →  0px        plain rectangles
sm     →  4px        chips, badges
base   →  8px        inputs, buttons, small cards (DEFAULT)
md     →  12px       cards, modals
lg     →  16px       large cards, sheets
xl     →  24px       hero cards
full   →  9999px     pills, avatars
```

**Rule:** never use the same radius on every element. The radius scale exists to create visual hierarchy. A button and a modal should not have the same radius.

### 2.6 Elevation

```
none   →  flat
sm     →  0 1px 2px rgba(0,0,0,0.05)              card on bg
md     →  0 4px 6px rgba(0,0,0,0.07)              dropdown
lg     →  0 10px 15px rgba(0,0,0,0.1)             modal
xl     →  0 20px 25px rgba(0,0,0,0.15)            popover
```

**Rule:** elevation is reserved for interactive surfaces. Static cards should not float.

### 2.7 Iconography

- **Library:** Lucide React (`lucide-react` package)
- **Sizes:** 16, 20, 24, 32 px (multiples of 4 only)
- **Stroke:** 2px default, 1.5px for 16px icons
- **Color:** inherits from text color; never coloured for decoration
- **Forbidden:** filled icons mixed with outline icons in the same view; 3D icons; gradient icons; emoji as icons

---

## 3. Information Architecture

### 3.1 Site Map

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              SITE MAP                                       │
│                                                                             │
│  /                                                                          │
│  ├── /auth/                                                                 │
│  │   ├── sign-up                                                            │
│  │   ├── sign-in                                                            │
│  │   ├── mfa            (TOTP / passkey challenge)                          │
│  │   └── forgot         (password reset)                                    │
│  │                                                                          │
│  ├── /onboarding/                                                           │
│  │   ├── welcome                                                            │
│  │   ├── account        (email/password + MFA enrollment)                   │
│  │   ├── identity       (phased: skipped unless data import attempted)      │
│  │   ├── demographics                                                       │
│  │   ├── conditions                                                         │
│  │   ├── disease        (conditional: only if cancer diagnosis selected)    │
│  │   ├── lifestyle                                                          │
│  │   ├── family                                                             │
│  │   └── summary                                                            │
│  │                                                                          │
│  ├── /dashboard/        (post-onboarding)                                   │
│  │   ├── /              (Home tab — default)                                │
│  │   ├── records                                                            │
│  │   │   ├── /          (longitudinal record browser)                       │
│  │   │   ├── timeline   (full chronological view)                           │
│  │   │   ├── labs       (lab values + trend charts)                         │
│  │   │   └── conflicts  (conflict resolution queue)                         │
│  │   ├── share                                                              │
│  │   │   ├── /          (active grants + create new)                        │
│  │   │   └── audit      (access audit log)                                  │
│  │   └── profile                                                            │
│  │       ├── /          (settings, account)                                 │
│  │       ├── connected  (EHR + wearable connections)                        │
│  │       ├── caregivers                                                     │
│  │       ├── consent    (research consent management)                       │
│  │       ├── export                                                         │
│  │       └── audit                                                          │
│  │                                                                          │
│  └── /r/{token}         (provider view, no auth required, scoped record)    │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 Primary Navigation

Four tabs in the dashboard, fixed position. Order matters: it's the order of patient priority.

```
┌──────────────┬──────────────┬──────────────┬──────────────┐
│   🏠 Home    │  📋 Records  │  🔗 Share    │  👤 Profile  │
└──────────────┴──────────────┴──────────────┴──────────────┘
```

**Why this order:**
1. **Home** — first thing the patient sees daily; the overview
2. **Records** — the main "job" of the app; browsing your health
3. **Share** — the action they take when meeting a doctor; needs to be findable
4. **Profile** — settings, exports, account; least frequent

**Mobile (≤ 768px):** bottom nav bar, fixed position, icon + label
**Desktop (≥ 1024px):** left sidebar, vertical, label + icon
**Tablet (769–1023px):** top nav bar, horizontal, label + icon

### 3.3 Visual Hierarchy Per Screen Type

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       UNIVERSAL HIERARCHY RULE                              │
│                                                                             │
│  PRIMARY    (1 thing)  →  What is this screen FOR?                         │
│                            Largest type, top-left, highest contrast         │
│                                                                             │
│  SECONDARY  (1-3)      →  What can the user DO here?                       │
│                            Medium type, right of primary or below           │
│                                                                             │
│  TERTIARY   (n)        →  What is the supporting CONTEXT?                  │
│                            Smaller type, muted color                         │
│                                                                             │
│  TRUST      (always)   →  Where did this DATA come from?                   │
│                            Smallest type, but always present                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

Every screen wireframe in §5 explicitly identifies its primary, secondary, tertiary, and trust signals.

---

## 4. Component Library

Built on **shadcn/ui** + Radix UI primitives + Tailwind CSS. All components follow the design tokens above.

### 4.1 Core Components (from shadcn/ui)

| Component | Purpose | Variants |
|---|---|---|
| `Button` | All actions | primary, secondary, ghost, destructive, link |
| `Input` | Text fields | text, email, password, number, search |
| `Textarea` | Multi-line text | default, minimal |
| `Select` | Dropdown selection | default, searchable, multi-select |
| `Checkbox` | Boolean toggle | default, with-label |
| `RadioGroup` | One-of-many | vertical, horizontal |
| `Switch` | On/off toggle | with-label, with-description |
| `Card` | Content container | flat, elevated, interactive |
| `Dialog` | Modal | default, sheet (mobile bottom-sheet) |
| `Sheet` | Slide-in panel | left, right, bottom |
| `Tabs` | Tab navigation | default, pills, underlined |
| `Accordion` | Collapsible | single-open, multi-open |
| `Toast` | Transient notification | info, success, warning, error |
| `Avatar` | User image | sm/md/lg, with-fallback |
| `Badge` | Label | default, outline, status (success/warning/error) |
| `Tooltip` | Hover hint | default, with-arrow |
| `Popover` | Click-triggered popup | default, with-arrow |
| `Progress` | Progress bar | linear, circular |
| `Skeleton` | Loading placeholder | text, card, image |

### 4.2 HealthKey-Specific Components

These are net-new components built on top of shadcn primitives.

#### `<CompletenessIndicator />`
Animated SVG circular progress, 64px diameter, shows profile completion %. Center text shows percentage. Outer ring color shifts: red (<30%), amber (30–70%), green (>70%).

```
       ╭───────╮
       │  72%  │       ← center text (h3, brand color)
       ╰───────╯
       ↓ supporting label
       Profile complete
```

#### `<DataSourceBadge />`
A small chip indicating data provenance. Always present near any health data.
```
[ FHIR · Epic · 2 hr ago ]    ← synced from EHR
[ Manual · You · just now ]   ← manually entered
[ AI · 87% confident ]        ← AI-extracted, with confidence
[ Document · Lab report ]     ← uploaded document
```

#### `<LabValueCard />`
Displays a single lab value with units, reference range, trend arrow, and time-series sparkline (last 6 measurements).
```
┌─────────────────────────────────────┐
│ Hemoglobin                  ↑       │  ← name + trend arrow
│ ────────────────────────────────────│
│ 12.5 g/dL                           │  ← large value (mono)
│ Normal range: 12.0–15.5             │  ← reference range (caption)
│                                     │
│ ▁▂▃▄▅▆ ───────                      │  ← sparkline (last 6 values)
│                                     │
│ [ FHIR · Epic · 3 days ago ]        │  ← provenance
└─────────────────────────────────────┘
```

#### `<LabTrendChart />`
Full-screen lab trend over time. Recharts line chart with:
- Reference range as a shaded band
- Out-of-range points highlighted with status color
- Hover/tap shows exact value, date, source
- Date range selector (1m / 3m / 6m / 1y / all)

#### `<ConflictResolutionCard />`
Shown when two providers report different values for the same field.
```
┌─────────────────────────────────────────────┐
│ ⚠ We found different values                │
│                                             │
│ Hemoglobin                                  │
│ ─────────────────────────────────────────── │
│ ○ 10.2 g/dL  · from Epic   · Mar 15        │
│ ○ 11.1 g/dL  · from Cerner · Mar 18 (newer)│
│                                             │
│ Which is correct?                           │
│ [Pick newer]  [Keep both]  [I don't know]  │
└─────────────────────────────────────────────┘
```

#### `<AccessGrantCard />`
Active sharing grant with countdown timer.
```
┌─────────────────────────────────────────────┐
│ Dr. Sarah Martinez                          │  ← who
│ Identity · Conditions · Labs                │  ← scopes (chips)
│                                             │
│ [████████░░] 6h 23m remaining               │  ← time bar
│                                             │
│ [ View QR ]  [ Copy link ]  [ Revoke ]      │
└─────────────────────────────────────────────┘
```

#### `<QRCodeModal />`
Full-screen modal with:
- HealthKey-branded QR code (logo in center)
- Animated horizontal scan line (subtle, 2s loop)
- Patient name + scope chips above QR
- Expiry countdown below QR
- Three actions: Save image · Copy link · Preview as recipient

#### `<OnboardingStepShell />`
Wrapper for every onboarding step. Provides:
- Top: progress bar + step counter (e.g. "Step 4 of 8")
- Top-right: "Skip for now" button (always visible, equal weight)
- Bottom: "Continue" button (primary) + "Back" (ghost)
- Auto-save indicator (subtle, top-right of content area)

#### `<ThreeModeInput />`
The defining UI pattern for data collection steps.
```
┌─────────────────────────────────────────────────────────┐
│  How would you like to add this?                        │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │   ✏️       │  │   📄      │  │   🔗      │              │
│  │  Type it  │  │  Upload   │  │  Connect  │              │
│  │   in      │  │  documents│  │  your EHR │              │
│  └──────────┘  └──────────┘  └──────────┘              │
│                                                          │
│  Or [ Skip for now ]                                    │
└─────────────────────────────────────────────────────────┘
```
Each card is keyboard-focusable, has hover/active states, and expands inline when selected (no modal).

#### `<DiseaseProfileTab />`
Tab strip for disease-specific clinical fields.
```
┌─────────────────────────────────────────────────────────┐
│ Multiple Myeloma Profile           [ Cancer fields ]    │  ← rose accent
│ ─────────────────────────────────────────────────────── │
│ [Staging] [Labs] [Markers] [Treatment] [Imaging]        │  ← sub-tabs
│ ─────────────────────────────────────────────────────── │
│                                                         │
│ ISS Stage:           [○ I  ○ II  ● III  ○ Unknown]      │
│ M-spike (serum):     [ 2.4 ] g/dL                        │
│ M-spike (urine):     [ 180 ] mg/24h                      │
│ ...                                                      │
└─────────────────────────────────────────────────────────┘
```

#### `<TimelineEntry />`
A single entry in the longitudinal timeline.
```
●  Mar 15 · 2026                      ← date + colored dot
│
│  Started Daratumumab                ← title (h4)
│  Treatment line 2 · 16 mg/kg weekly ← detail (body)
│  [ FHIR · Cerner ]                  ← provenance (caption)
```
Dot color encodes event type: blue (treatment), purple (diagnosis), green (lab), amber (procedure), gray (other).

---

## 5. Screen Inventory & Wireframes

ASCII wireframes for every key screen. The wireframes show **structure and hierarchy**, not pixel-perfect layout. Pixel layout is the implementer's job, guided by the design system above.

### 5.1 Sign Up — `/auth/sign-up`

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│                       ┌─────────────────────────────┐                   │
│                       │  HealthKey                  │  ← brand wordmark │
│                       └─────────────────────────────┘                   │
│                                                                         │
│                          Create your account                            │  ← h1
│                                                                         │
│                  Take control of your health record.                    │  ← body, muted
│                                                                         │
│                       ┌─────────────────────────────┐                   │
│                       │  Continue with Apple        │                   │  ← social buttons
│                       └─────────────────────────────┘                   │
│                       ┌─────────────────────────────┐                   │
│                       │  Continue with Google       │                   │
│                       └─────────────────────────────┘                   │
│                                                                         │
│                       ──────── or ────────                              │
│                                                                         │
│                       Email                                             │
│                       [                              ]                  │
│                                                                         │
│                       Password                                          │
│                       [                          ] 👁                   │  ← show/hide toggle
│                       [████████░░░░] Strong                             │  ← strength meter
│                       8+ chars · uppercase · number · special           │
│                                                                         │
│                       ☐ I agree to the Terms and Privacy Policy         │
│                                                                         │
│                       ┌─────────────────────────────┐                   │
│                       │  Create account             │                   │  ← primary CTA
│                       └─────────────────────────────┘                   │
│                                                                         │
│                       Already have an account?  Sign in                 │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Hierarchy:** Brand → "Create your account" → email/password → CTA → terms.
**Trust:** No "trusted by" logos. No "join 100k users" line. Restraint signals seriousness.
**Forbidden:** No hero image. No "Welcome to HealthKey" blob. No marketing copy.

### 5.2 Onboarding Welcome — `/onboarding/welcome`

```
┌─────────────────────────────────────────────────────────────────────────┐
│ [████░░░░░░░░░░░░░░░░░░] Step 1 of 8         [ Skip for now ]           │
│                                                                         │
│                                                                         │
│                                                                         │
│                                                                         │
│                          Welcome, Sarah                                 │  ← h1, friendly
│                                                                         │
│                We'll help you build a complete picture of               │  ← body-lg
│                your health. This takes about 5 minutes.                 │
│                                                                         │
│                You can skip any step. Nothing is required.              │
│                                                                         │
│                                                                         │
│                          ┌────────────┐                                  │
│                          │  Continue  │                                  │
│                          └────────────┘                                  │
│                                                                         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**Hierarchy:** Greeting → reassurance → action.
**Why "you can skip" appears here:** lowering anxiety upfront is the highest-leverage onboarding move.

### 5.3 Onboarding Step (Conditions) — `/onboarding/conditions`

```
┌─────────────────────────────────────────────────────────────────────────┐
│ [████████░░░░░░░░░░░░░░] Step 4 of 8         [ Skip for now ]           │
│                                                                         │
│  Conditions and diagnoses                                               │  ← h1
│                                                                         │
│  Add anything you know. We'll fill in the rest from your records.       │  ← body-lg, muted
│                                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                              │
│  │   ✏️       │  │   📄      │  │   🔗      │                              │
│  │  Type it  │  │  Upload   │  │  Connect  │                              │
│  │   in      │  │  documents│  │  your EHR │                              │
│  └──────────┘  └──────────┘  └──────────┘                              │
│                                                                         │
│  Common conditions                                                      │  ← h3
│  ┌──────────┐ ┌──────────┐ ┌─────────┐ ┌──────┐ ┌─────────────┐         │
│  │ Diabetes │ │Hypertens.│ │ Asthma  │ │ COPD │ │ Heart disease│         │  ← chips
│  └──────────┘ └──────────┘ └─────────┘ └──────┘ └─────────────┘         │
│  ┌──────────────┐ ┌──────────┐ ┌─────────────┐ ┌────────────┐           │
│  │Hypothyroidism│ │ Arthritis│ │Depression/Anx│ │ IBS/Crohn's│           │
│  └──────────────┘ └──────────┘ └─────────────┘ └────────────┘           │
│                                                                         │
│  Cancer diagnosis (optional)                                  🌹         │  ← rose accent
│  ┌─────────────────────────────────────┐                                │
│  │ Choose if applicable             ▾   │                                │  ← Select
│  └─────────────────────────────────────┘                                │
│                                                                         │
│  ─────────────────────────────────────────────────────────────────────  │
│                                                                         │
│  [ ◀ Back ]                              [ Continue ▶ ]                 │
└─────────────────────────────────────────────────────────────────────────┘
```

**Auto-save:** Every chip click PATCHes the patient profile. No "Save" button. A subtle "Saved" indicator appears top-right for 1.5s after each change.
**Cancer field accent:** rose color used **only** to visually separate cancer-specific fields from general health. Never used for decoration elsewhere.

### 5.4 Disease Profile (Multiple Myeloma) — `/onboarding/disease`

```
┌─────────────────────────────────────────────────────────────────────────┐
│ [██████████████░░░░░░░░] Step 7 of 8         [ Skip for now ]           │
│                                                                         │
│  Multiple Myeloma profile                                    🌹          │  ← h1, rose accent
│                                                                         │
│  These details help us match you to relevant clinical trials and        │
│  standard-of-care recommendations. All fields are optional.             │
│                                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                              │
│  │  Type it │  │  Upload  │  │  Connect │                              │
│  └──────────┘  └──────────┘  └──────────┘                              │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  [Staging]  [Labs]  [Markers]  [Treatment]  [Imaging]           │    │  ← sub-tabs
│  ├─────────────────────────────────────────────────────────────────┤    │
│  │                                                                  │    │
│  │  ISS Stage                                                       │    │
│  │  ○ Stage I    ○ Stage II    ● Stage III    ○ Unknown            │    │
│  │                                                                  │    │
│  │  Disease status                                                  │    │
│  │  [ Newly diagnosed                              ▾ ]              │    │
│  │                                                                  │    │
│  │  ECOG performance status        ⓘ                                │    │
│  │  ○ 0 (fully active)                                              │    │
│  │  ● 1 (some symptoms but ambulatory)                              │    │
│  │  ○ 2 (limited activity, in bed <50%)                             │    │
│  │  ○ 3 (limited self-care, in bed >50%)                            │    │
│  │  ○ 4 (completely disabled)                                       │    │
│  │                                                                  │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  [ ◀ Back ]                              [ Continue ▶ ]                 │
└─────────────────────────────────────────────────────────────────────────┘
```

**Plain-language hint:** ECOG values shown with their plain-language meaning. The `ⓘ` icon opens a tooltip with the medical definition.
**Forbidden:** Never show "ECOG = 1" with no explanation.

### 5.5 Onboarding Summary — `/onboarding/summary`

```
┌─────────────────────────────────────────────────────────────────────────┐
│ [████████████████████████] Complete                                     │
│                                                                         │
│                                                                         │
│                          ╭─────────╮                                     │
│                          │   72%   │                                     │  ← circular indicator
│                          ╰─────────╯                                     │
│                                                                         │
│                       Your profile is 72% complete                      │  ← h2
│                                                                         │
│                  Great start. You can fill in more anytime.             │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  ✓  Demographics                     100%                       │    │
│  │  ✓  Conditions                        85%                       │    │
│  │  ◐  Disease profile (myeloma)         60%                       │    │
│  │  ◐  Lifestyle                         70%                       │    │
│  │  ○  Family history                     0%   [ Add now ]         │    │
│  │  ◐  Lab values                        40%                       │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  Recommended next                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  🔗  Connect your provider                                       │    │
│  │     Pull in records from your hospital automatically.            │    │
│  │                                            [ Connect ]           │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  Go to my dashboard                                              │    │  ← primary CTA
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  [ Start over ]                                                         │  ← ghost button, small
└─────────────────────────────────────────────────────────────────────────┘
```

**Why % per category:** patients want to know what's missing without clicking through every step.

### 5.6 Dashboard / Home Tab — `/dashboard`

```
┌─────────────────────────────────────────────────────────────────────────┐
│  HealthKey                                          🔔   👤             │  ← top bar
│ ─────────────────────────────────────────────────────────────────────── │
│                                                                         │
│  Good morning, Sarah                              ╭─────╮               │
│                                                   │ 72% │               │  ← greeting + completeness
│  Your record is up to date.                       ╰─────╯               │
│                                                                         │
│  Quick actions                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐                │
│  │   🔗      │  │   ➕      │  │   🎯      │  │   ⬇       │                │
│  │  Share   │  │ Add data │  │  Trials  │  │  Export  │                │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘                │
│                                                                         │
│  Recent activity                                                        │  ← h3
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  ●  New lab results from Epic            2 hours ago           │    │
│  │  ●  Profile updated by you               yesterday              │    │
│  │  ●  Connected athenahealth               3 days ago             │    │
│  │                                          [ See all activity ]   │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  Sections                                                               │  ← h3
│  ┌────────────────────────────┐  ┌────────────────────────────┐         │
│  │ Identity                   │  │ Conditions                 │         │
│  │ ────────────────────────── │  │ ────────────────────────── │         │
│  │ Sarah Martinez             │  │ Multiple myeloma · Stage 3 │         │
│  │ DOB · 1968 · Female        │  │ Hypertension · diagnosed   │         │
│  │ ✓ VERIFIED                 │  │ 100% complete              │         │
│  └────────────────────────────┘  └────────────────────────────┘         │
│  ┌────────────────────────────┐  ┌────────────────────────────┐         │
│  │ Latest labs                │  │ Drug allergies            ⚠ │         │
│  │ ────────────────────────── │  │ ────────────────────────── │         │
│  │ Hemoglobin   12.5  ↑       │  │ Penicillin                 │         │
│  │ Creatinine   1.1   →       │  │ Sulfa drugs                │         │
│  │ [ FHIR · Epic ]            │  │ [ Manual · You ]           │         │
│  └────────────────────────────┘  └────────────────────────────┘         │
│                                                                         │
│ ─────────────────────────────────────────────────────────────────────── │
│  🏠 Home    📋 Records    🔗 Share    👤 Profile                        │  ← bottom nav (mobile)
└─────────────────────────────────────────────────────────────────────────┘
```

**Hierarchy:** Greeting + completeness → quick actions → recent activity → record sections.
**Why this order:** patient opens app → wants to know "is everything OK?" → completeness answers that → then they want to take an action → quick actions surface the four most common ones.

### 5.7 Records Tab — `/dashboard/records`

```
┌─────────────────────────────────────────────────────────────────────────┐
│  HealthKey                                          🔔   👤             │
│ ─────────────────────────────────────────────────────────────────────── │
│                                                                         │
│  Your records                                                           │  ← h1
│                                                                         │
│  [ All ] [ Identity ] [ Conditions ] [ Labs ] [ Family ] [ Sources ]    │  ← filter chips
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  ⚠ 2 conflicts need your attention                              │    │  ← alert banner
│  │     Different providers reported different values.              │    │
│  │                                       [ Review now ]            │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  Identity                                                       ✏        │  ← h3 + edit
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  Sarah Martinez                                                  │    │
│  │  Born 1968 · Female · 5'6" · 145 lbs                            │    │
│  │  ✓ Identity verified  · IAL2                                    │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  Conditions                                                     ✏        │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  Active                                                          │    │
│  │  • Multiple myeloma · ISS Stage III · diagnosed Mar 2024        │    │
│  │  • Hypertension · diagnosed 2019                                 │    │
│  │                                                                  │    │
│  │  [ FHIR · Epic, Cerner ]                                        │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  Drug allergies                                          ⚠               │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  • Penicillin — anaphylaxis (severe)                            │    │
│  │  • Sulfa drugs — rash                                            │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  Labs                                                      [ See all ]  │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐     │   │
│  │ │ Hemoglobin │ │ Creatinine │ │ Platelets  │ │   M-spike  │     │   │
│  │ │ 12.5 g/dL  │ │ 1.1 mg/dL  │ │ 145 K/uL   │ │ 2.4 g/dL   │     │   │
│  │ │ ↑ improving│ │ → stable   │ │ ↓ low      │ │ ↓ improving│     │   │
│  │ │ ▁▂▃▄▅▆     │ │ ▅▅▅▅▅▅     │ │ ▆▅▄▃▂▁     │ │ ▆▅▄▃▂▁     │     │   │
│  │ └────────────┘ └────────────┘ └────────────┘ └────────────┘     │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  Connected sources                                                      │
│  ┌──────────────────────────┐  ┌──────────────────────────┐             │
│  │ Epic · Mass General      │  │ Apple Health             │             │
│  │ Synced 2h ago     [LIVE] │  │ Auto-sync         [SYNC] │             │
│  └──────────────────────────┘  └──────────────────────────┘             │
│                                                                         │
│ ─────────────────────────────────────────────────────────────────────── │
│  🏠    📋 Records    🔗    👤                                            │
└─────────────────────────────────────────────────────────────────────────┘
```

**Why grouped by category, not source:** the patient thinks "where are my labs?" not "what did Epic send me?"
**Conflict banner:** persistent until resolved. Actionable, not decorative.

### 5.8 Lab Trend Chart — `/dashboard/records/labs/{field}`

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ◀ Back to records                                                      │
│                                                                         │
│  Hemoglobin                                                             │  ← h1
│                                                                         │
│  12.5 g/dL                                              ↑ improving     │  ← current value (mono, large)
│  Last measured Mar 18 · Epic                                            │
│                                                                         │
│  [ 1m ] [ 3m ] [ 6m ] [ 1y ] [ All ]                                    │  ← range selector
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  16 ┤                                                            │    │
│  │  15 ┤                                                            │    │
│  │  14 ┤  ╭───────────────╮                                         │    │  ← reference range
│  │  13 ┤  │           ●   │                                         │    │     (shaded band)
│  │  12 ┤  │     ●         │       ●                                 │    │
│  │  11 ┤  │  ●            │  ●                                      │    │
│  │  10 ┤  │               ╰──●  ←out of range                       │    │
│  │   9 ┤  │               │                                         │    │
│  │     └────────────────────────────────────────                    │    │
│  │      Jan   Feb   Mar   Apr   May   Jun                           │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  Normal range: 12.0–15.5 g/dL                                           │
│                                                                         │
│  Recent measurements                                                    │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  Mar 18  ·  12.5 g/dL  ·  Epic            ↑                     │    │
│  │  Mar 02  ·  11.8 g/dL  ·  Epic            ↑                     │    │
│  │  Feb 15  ·  10.9 g/dL  ·  Cerner   below  ↑                     │    │
│  │  Feb 01  ·  10.2 g/dL  ·  Cerner   below  ↓                     │    │
│  │  Jan 18  ·  10.6 g/dL  ·  Cerner   below                        │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

**Out-of-range highlight:** below-range values get an amber dot and "below" label. Not red — red is reserved for critical/error states. Out-of-range is concerning, not an emergency.

### 5.9 Conflict Resolution — `/dashboard/records/conflicts`

```
┌─────────────────────────────────────────────────────────────────────────┐
│  ◀ Back to records                                                      │
│                                                                         │
│  Resolve conflicts                                                      │  ← h1
│                                                                         │
│  We found 2 places where your providers disagree. You can pick the     │
│  most accurate version, or keep both for your records.                  │
│                                                                         │
│  Conflict 1 of 2                                                        │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  Hemoglobin                                                      │    │
│  │  ─────────────────────────────────────────────────────────────  │    │
│  │                                                                  │    │
│  │  ◯  10.2 g/dL                                                    │    │
│  │      from Epic · Massachusetts General · Mar 15                  │    │
│  │      [ FHIR · verified ]                                        │    │
│  │                                                                  │    │
│  │  ◉  11.1 g/dL                                  (newer)          │    │
│  │      from Cerner · Brigham & Women's · Mar 18                    │    │
│  │      [ FHIR · verified ]                                        │    │
│  │                                                                  │    │
│  │  Why might these differ?                                        │    │
│  │  Different labs use different equipment, and your hemoglobin    │    │
│  │  may have changed between measurements.                          │    │
│  │                                                                  │    │
│  │  [ Pick newer ]   [ Keep both ]   [ I'm not sure — skip ]      │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
```

**Plain-language explanation:** patients are not clinicians. Why values differ matters as much as which value to keep.
**"I'm not sure" is not a failure path.** Skipping is fine. The conflict stays in the queue.

### 5.10 Share Tab — `/dashboard/share`

```
┌─────────────────────────────────────────────────────────────────────────┐
│  HealthKey                                          🔔   👤             │
│ ─────────────────────────────────────────────────────────────────────── │
│                                                                         │
│  Share your record                                                      │  ← h1
│                                                                         │
│  Create time-limited access for a doctor or caregiver. They'll see      │
│  only what you choose. You can revoke access anytime.                   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  Create new share                                                │    │  ← primary CTA card
│  │                                                                  │    │
│  │  Who is this for?     [ e.g., Dr. Martinez                  ]   │    │
│  │                                                                  │    │
│  │  What can they see?   ☑ Identity                                │    │
│  │                       ☑ Conditions                              │    │
│  │                       ☑ Labs                                    │    │
│  │                       ☐ Disease profile                         │    │
│  │                       ☐ Family history                          │    │
│  │                                                                  │    │
│  │  How long?            ○ 1 hour  ○ 24 hours  ● 7 days           │    │
│  │                       ○ 30 days  ○ One-time                     │    │
│  │                                                                  │    │
│  │  [ Add passcode (optional) ]                                    │    │
│  │                                                                  │    │
│  │                                       [ Generate share ]        │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  Active grants                                                          │  ← h3
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  Dr. Sarah Martinez                                              │    │
│  │  Identity · Conditions · Labs                                    │    │
│  │  [████████░░] 6h 23m remaining                                   │    │
│  │  [ View QR ]   [ Copy link ]   [ Revoke ]                       │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  Brigham & Women's Hospital                                      │    │
│  │  All scopes                                                      │    │
│  │  [██░░░░░░░░] 1d 4h remaining                                    │    │
│  │  [ View QR ]   [ Copy link ]   [ Revoke ]                       │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  [ View access history ]                                                │
│                                                                         │
│ ─────────────────────────────────────────────────────────────────────── │
│  🏠    📋    🔗 Share    👤                                              │
└─────────────────────────────────────────────────────────────────────────┘
```

### 5.11 QR Code Modal

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                          ✕              │  ← close
│                                                                         │
│                       Sarah Martinez                                    │  ← patient name
│                       Identity · Conditions · Labs                      │  ← scope chips
│                                                                         │
│                    ┌───────────────────────────┐                        │
│                    │  ███████  ████  █  █████  │                        │
│                    │  █     █  █  █  █  █   █  │                        │
│                    │  █ ███ █  ████  █  █████  │                        │
│                    │  █ ███ █     █  █     ██  │                        │
│                    │  █ ███ █  ████  █  █████  │                        │
│                    │  █     █  ████  █  █████  │                        │  ← QR with brand logo center
│                    │  ███████  █  █  ████████  │                        │
│                    │   ───────────  ←scan line │                        │  ← animated 2s loop
│                    │  ████  █  ████  ████   █  │                        │
│                    └───────────────────────────┘                        │
│                                                                         │
│                       Expires in 6h 23m                                 │
│                                                                         │
│        [ Save image ]   [ Copy link ]   [ Preview as recipient ]        │
└─────────────────────────────────────────────────────────────────────────┘
```

### 5.12 Provider View — `/r/{token}`

```
┌─────────────────────────────────────────────────────────────────────────┐
│  HealthKey · Provider view                          ⏱ 5h 47m            │  ← branded bar + countdown
│ ─────────────────────────────────────────────────────────────────────── │
│  Sarah Martinez · Born 1968 · Female                                    │
│  Shared by patient · Identity, Conditions, Labs                         │  ← scope chips
│ ─────────────────────────────────────────────────────────────────────── │
│                                                                         │
│  Read-only view · Cannot be downloaded or re-shared                     │  ← watermark notice
│                                                                         │
│  Identity                                                               │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  Sarah Martinez                                                  │    │
│  │  DOB Apr 14, 1968 · Female · 5'6" · 145 lbs                     │    │
│  │  ✓ Verified · IAL2                                              │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  Active conditions                                                      │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  • Multiple myeloma · ISS Stage III · diagnosed Mar 2024        │    │
│  │     ECOG 1 · Lambda light chain                                  │    │
│  │  • Hypertension · diagnosed 2019                                 │    │
│  │  Source: Epic, Cerner                                            │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  Drug allergies ⚠                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  • Penicillin — anaphylaxis                                      │    │
│  │  • Sulfa — rash                                                  │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  Recent labs                                                            │
│  [ ... lab cards ... ]                                                  │
│                                                                         │
│  ─────────────────────────────────────────────────────────────────────  │
│  [ Request more access ]                                  [ Done ]      │
└─────────────────────────────────────────────────────────────────────────┘
```

**No editing.** No "save to my system" button. The provider view is intentionally a dead end — the patient owns the record.

### 5.13 Profile Tab — `/dashboard/profile`

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Profile                                                                │  ← h1
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  Sarah Martinez                                                  │    │
│  │  sarah.m@example.com                                             │    │
│  │  ✓ Identity verified · IAL2                                     │    │
│  │                                                  [ Edit ]        │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  Connected accounts                                                     │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  Epic · Mass General             Synced 2h ago        [LIVE]    │    │
│  │  Cerner · Brigham                Synced yesterday     [LIVE]    │    │
│  │  Apple Health                    Auto-sync            [SYNC]    │    │
│  │                                            [ Connect new ]      │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  Caregivers                                                             │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  John Martinez (spouse)          Can view, add notes            │    │
│  │  Dr. Lee (oncologist)            Can view                        │    │
│  │                                            [ Add caregiver ]    │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  Research consent                                                       │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  ☑ Multiple myeloma research cohort     Joined Mar 2026         │    │
│  │  ☐ Cancer survivor outcomes study                                │    │
│  │                                            [ Manage ]            │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  Settings                                                               │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  Notifications                              [ Manage ]           │    │
│  │  Two-factor authentication                  Enabled              │    │
│  │  Biometric lock                             [○]                  │    │
│  │  Auto-sync wearables                        [●]                  │    │
│  │  Theme                                      System ▾             │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  Your data                                                              │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  Export as FHIR R4                          [ Download ]         │    │
│  │  Export as PDF summary                      [ Download ]         │    │
│  │  Export as OMOP                             [ Download ]         │    │
│  │  Access audit log                           [ View ]             │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                         │
│  Legal                                                                  │
│  Terms of Service · Privacy Policy · Sign out                           │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 6. Interaction State Coverage

Every screen specifies all five states. No "we'll figure it out later."

```
┌──────────────────────┬─────────────┬─────────────┬─────────────┬──────────────┬──────────────┐
│  FEATURE              │  LOADING    │  EMPTY      │  ERROR      │  SUCCESS     │  PARTIAL     │
├──────────────────────┼─────────────┼─────────────┼─────────────┼──────────────┼──────────────┤
│  Sign up              │  Btn spin   │  N/A        │  Inline     │  → MFA       │  N/A         │
│                       │             │             │  field err  │              │              │
├──────────────────────┼─────────────┼─────────────┼─────────────┼──────────────┼──────────────┤
│  Onboarding step      │  Skeleton   │  Hint:      │  Toast +    │  Saved       │  Auto-save   │
│                       │  fields     │  "Type or   │  retry      │  indicator   │  per field   │
│                       │             │  upload"    │             │              │              │
├──────────────────────┼─────────────┼─────────────┼─────────────┼──────────────┼──────────────┤
│  Dashboard home       │  Skeleton   │  "No        │  Banner     │  N/A         │  Section %   │
│                       │  cards      │  records    │  with retry │              │  shown       │
│                       │             │  yet" CTA   │             │              │              │
├──────────────────────┼─────────────┼─────────────┼─────────────┼──────────────┼──────────────┤
│  Records browser      │  Skeleton   │  "Add your  │  "Couldn't  │  N/A         │  Mixed       │
│                       │  category   │  first      │  load some  │              │  source list │
│                       │  cards      │  record"    │  records"   │              │              │
├──────────────────────┼─────────────┼─────────────┼─────────────┼──────────────┼──────────────┤
│  Lab trend chart      │  Skeleton   │  "No data   │  Inline     │  Chart +     │  Sparse      │
│                       │  chart      │  yet"       │  message    │  data table  │  data: dots  │
│                       │             │             │             │              │  not lines   │
├──────────────────────┼─────────────┼─────────────┼─────────────┼──────────────┼──────────────┤
│  Conflict resolution  │  Skeleton   │  "No        │  Inline     │  Banner +    │  N/A         │
│                       │  card       │  conflicts  │  per-card   │  next item   │              │
│                       │             │  found 🎉"  │             │              │              │
├──────────────────────┼─────────────┼─────────────┼─────────────┼──────────────┼──────────────┤
│  EHR sync             │  Pulse      │  N/A        │  "Couldn't  │  "Synced     │  "X of Y     │
│                       │  badge      │             │  reach Epic │  just now"   │  records     │
│                       │             │             │  — retry"   │              │  imported"   │
├──────────────────────┼─────────────┼─────────────┼─────────────┼──────────────┼──────────────┤
│  Document upload      │  Progress   │  N/A        │  "Upload    │  "X fields   │  "Y of Z     │
│                       │  bar        │             │  failed —   │  found"      │  fields      │
│                       │             │             │  retry"     │              │  extracted"  │
├──────────────────────┼─────────────┼─────────────┼─────────────┼──────────────┼──────────────┤
│  AI extraction        │  "Reading…" │  "We        │  "Couldn't  │  Review      │  Some fields │
│                       │  spinner    │  couldn't   │  process    │  panel       │  low conf:   │
│                       │             │  find any   │  this doc"  │              │  flagged     │
│                       │             │  fields"    │             │              │              │
├──────────────────────┼─────────────┼─────────────┼─────────────┼──────────────┼──────────────┤
│  Share tab            │  Skeleton   │  "No active │  Inline     │  Toast       │  N/A         │
│                       │  cards      │  shares"    │  per-grant  │              │              │
├──────────────────────┼─────────────┼─────────────┼─────────────┼──────────────┼──────────────┤
│  Create share         │  Btn spin   │  N/A        │  Inline     │  → QR modal  │  N/A         │
│                       │             │             │             │              │              │
├──────────────────────┼─────────────┼─────────────┼─────────────┼──────────────┼──────────────┤
│  Provider view /r/    │  Skeleton   │  N/A        │  410 Gone:  │  N/A         │  Scoped      │
│                       │  bundle     │             │  expired/   │              │  data only   │
│                       │             │             │  revoked    │              │              │
├──────────────────────┼─────────────┼─────────────┼─────────────┼──────────────┼──────────────┤
│  Trial matching       │  "Searching │  "No trials │  "Couldn't  │  Ranked      │  Some        │
│                       │  trials…"   │  matched"   │  reach trial│  list        │  matches +   │
│                       │             │             │  service"   │              │  reasons     │
└──────────────────────┴─────────────┴─────────────┴─────────────┴──────────────┴──────────────┘
```

### Empty state principles

Empty states are **features**, not afterthoughts. Every empty state has:
1. **Warmth** — never "No items found." Instead: "No conflicts found 🎉 Your records all agree."
2. **Primary action** — what should the user do next? A button with the obvious next step.
3. **Context** — why is it empty? "We'll show new lab results here once you connect a provider."

### Error state principles

1. **Plain language** — never "ERR_NETWORK_TIMEOUT (504)". Instead: "Couldn't reach Epic. Check your connection and try again."
2. **Recoverable** — always provide a retry action. Never a dead end.
3. **Don't blame the user** — even if they fat-fingered a password, the message is "Password didn't match. Try again." not "Invalid credentials."

---

## 7. User Journey & Emotional Arc

### 7.1 First-time patient journey

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    NEW PATIENT — DAY 1 EMOTIONAL ARC                        │
│                                                                             │
│  Step              Action           Feeling           Design supports it    │
│  ──────────────── ──────────────── ──────────────── ──────────────────────  │
│                                                                             │
│  1. Land           Click signup    Cautious /        Calm wordmark, no     │
│                                    overwhelmed       hero image, plain      │
│                                                       headline              │
│                                                                             │
│  2. Sign up        Email/password  Wary about        No "Trusted by"       │
│                                    health data       logos. T&C visible.   │
│                                                                             │
│  3. Welcome        Read intro      Hopeful but       "Skip any step"       │
│                                    guarded           shown upfront         │
│                                                                             │
│  4. Demographics   Type name/DOB   Bored,            Auto-save invisible.  │
│                                    transactional     No friction.          │
│                                                                             │
│  5. Conditions     Pick chips      Uncomfortable,    Familiar chips not    │
│                                    facing diagnosis  scary medical forms   │
│                                                                             │
│  6. Disease        Stage, ECOG     Vulnerable —      Plain language with   │
│     profile        markers         this is real      tooltips. Can skip.   │
│                                                                             │
│  7. Lifestyle      Smoking, diet   Mildly judged     Neutral framing,      │
│                                                       no praise/scolding    │
│                                                                             │
│  8. Family         Relative grid   Some grief        Toggle grid is fast,  │
│                                                       no narrative form     │
│                                                                             │
│  9. Summary        See 72%         Accomplishment    Animated circle, but  │
│                    complete                          no confetti           │
│                                                                             │
│  10. Connect EHR   OAuth flow      "Will this        Source list shown.    │
│      (optional)                    actually work?"   Status badge real-time│
│                                                                             │
│  11. First sync    Wait 30s        Anxious           Progress not spinner. │
│                                                       "Importing 142 of    │
│                                                       287 records"         │
│                                                                             │
│  12. Records       Browse own     Relief +          Categories not raw    │
│      populate      record         curiosity         FHIR. Plain language.  │
│                                                                             │
│  13. Find a        Spot mistake   Annoyed but       Conflict UI is        │
│      conflict      from Epic      empowered         calm, explanatory.    │
│                                                                             │
│  14. Share with    Generate QR    Slight pride      QR is clean, branded  │
│      doctor                                          but not corporate     │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Key insight:** the patient's emotional state changes from "wary" → "vulnerable" → "relief". The design must NEVER spike the emotion in the wrong direction. No celebration animations on completing the disease profile step. No "Way to go!" microcopy when adding allergies. Calm before clever.

### 7.2 Returning patient — daily check

```
1. Open app  →  see "Good morning, Sarah" + 72% completeness
2. Glance at "Recent activity" → "New labs from Epic 2h ago"
3. Tap labs → see hemoglobin trending up
4. Done. App closed. 23 seconds total.
```

The home tab is optimised for this 23-second daily glance. NOT for engagement metrics. NOT for "session length". The patient wants to know they're OK, then leave.

### 7.3 Pre-appointment journey

```
1. Day before appointment → patient remembers to share record
2. Open Share tab → tap "Create new share"
3. Type doctor's name, pick scopes, pick "24 hours"
4. Generate → QR shown
5. Save image to phone or screenshot
6. Day of appointment → show QR to doctor's tablet
7. Doctor scans → sees scoped record on their device
8. Appointment ends → patient revokes (or grant auto-expires)
```

**Speed matters here.** From "open app" to "QR ready" should be under 30 seconds. The Share tab has the create form expanded by default (not hidden behind a button).

---

## 8. Responsive Behavior

### 8.1 Breakpoints

```
mobile      ≤ 640px      iPhone, small Android
mobile-lg   641–768px    larger phones, small tablets portrait
tablet      769–1024px   iPad portrait, small laptops
desktop     1025–1440px  laptops, monitors
desktop-xl  > 1440px     large monitors
```

Mobile-first. Desktop is an enhancement, not the baseline.

### 8.2 Layout adaptations

| Element | Mobile (≤ 640) | Tablet (769–1024) | Desktop (≥ 1025) |
|---|---|---|---|
| Primary nav | Bottom bar (icon + label) | Top bar (label + icon) | Left sidebar (vertical) |
| Page padding | 16px | 24px | 40px |
| Onboarding | 1 column, full width | 1 column, max 480px | 1 column, max 560px, centered |
| Records cards | 1 column stacked | 2 columns | 2 columns max width 640px each |
| Lab card grid | 2 columns | 3 columns | 4 columns |
| Share form | Full width, sheet over content | Inline card | Inline card, max 640px |
| QR modal | Bottom sheet, full width | Centered modal, 480px | Centered modal, 480px |
| Provider view | 1 column | 1 column max 720px | 1 column max 720px centered |
| Conflict cards | 1 column, full width | 1 column, max 640px | 1 column, max 720px |

### 8.3 Mobile-specific patterns

- **Bottom sheet over modal** — modals on phones are anti-pattern. Use Radix `Sheet` with `side="bottom"`.
- **Sticky CTAs** — onboarding "Continue" stays at the bottom of viewport, not at the bottom of content.
- **Keyboard handling** — focus inputs auto-scroll above the keyboard. Test on iOS Safari.
- **Pull-to-refresh** — Records tab supports pull-to-refresh to trigger sync.
- **Touch targets ≥ 44px** — never put two interactive elements within 8px of each other.

---

## 9. Accessibility Specifications

WCAG 2.1 AA minimum. AAA where viable. **Health apps have an above-average proportion of users with disabilities** — visual impairment from diabetic retinopathy, motor impairment from chemo neuropathy, cognitive impairment from chemo brain. This isn't a checkbox.

### 9.1 Keyboard Navigation

- All interactive elements reachable via Tab in logical order
- Focus rings visible (2px solid `brand-700`, 2px offset)
- Skip-to-content link as first focusable element on every page
- Modal focus trap with `Esc` to close
- Custom selects (chip groups, radio groups) use arrow key navigation per ARIA spec
- All buttons have keyboard equivalents (Space and Enter)
- No keyboard traps anywhere

### 9.2 Screen Reader Support

- Semantic HTML first: `<header>`, `<nav>`, `<main>`, `<aside>`, `<footer>`
- ARIA landmarks: `role="banner"`, `role="navigation"`, `role="main"`, `role="contentinfo"`
- Form labels always present (visible or `aria-label`)
- Form errors announced via `aria-live="assertive"`
- Toast notifications announced via `aria-live="polite"`
- Lab values include unit announcements: `aria-label="Hemoglobin 12.5 grams per deciliter"`
- Chart accessibility: data table fallback always present, charts have `role="img"` with summary
- Decorative icons have `aria-hidden="true"`
- Status icons have `aria-label` ("verified", "out of range", "syncing")

### 9.3 Color & Contrast

- Body text: 4.5:1 minimum (AA)
- Large text (≥ 18px): 3:1 minimum
- UI components and graphical objects: 3:1
- **Never use color alone to convey information.** Out-of-range labs have a label AND a color. Required fields have an asterisk AND a color.
- Dark mode tested with same contrast requirements
- Tested with simulated red-green color blindness (Deuteranopia)

### 9.4 Touch & Motor

- Touch targets ≥ 44 × 44 px
- Spacing between targets ≥ 8 px
- No hover-only interactions (always provide click/tap equivalent)
- Drag interactions have keyboard equivalents
- No time-limited interactions without warning + extension

### 9.5 Cognitive

- Plain-language clinical terms always have definitions accessible
- One primary action per screen, clearly distinguished
- No auto-advancing carousels
- No flashing content
- Error messages explain WHAT to do, not just what went wrong
- Forms can be saved partially, returned to later
- Confirmation for destructive actions (revoke share, delete account)

### 9.6 Assistive Tech Tested

- VoiceOver (iOS, macOS Safari)
- TalkBack (Android Chrome)
- NVDA (Windows Firefox)
- JAWS (Windows Chrome)
- Voice Control (iOS, macOS)
- Switch Control (iOS)

---

## 10. Microcopy Guidelines

The voice and tone is **calm, plain, honest, never cute, never marketing**.

### 10.1 Voice principles

- **Plain over precise.** "Your activity level" not "ECOG performance status."
- **Honest about uncertainty.** "We think this is your hemoglobin value (87% confident)" not "Hemoglobin: 12.5".
- **Never celebrate medical events.** "Profile complete" not "Way to go! You're crushing it!"
- **Use the patient's words.** "Heart attack" not "myocardial infarction" (unless clinical context demands it).
- **Active voice.** "We'll send you a reminder" not "A reminder will be sent."
- **Short sentences.** 12 words or fewer when possible.
- **No emoji in clinical contexts.** OK in onboarding welcome ("🎉 You're done"), forbidden in records or conflict resolution.

### 10.2 Examples

**Forbidden:**
- "Welcome to HealthKey, your all-in-one health companion!"
- "🚀 Let's boost your health journey!"
- "Crushing it! Your profile is now 80% complete."
- "Oops! Something went wrong. Please try again."
- "Your data is being synced. Please wait..."
- "ERR_NETWORK_TIMEOUT_504"

**Use instead:**
- "Take control of your health record."
- "Let's start with the basics."
- "Profile is 80% complete."
- "Couldn't save. Check your connection and try again."
- "Importing 142 of 287 records from Epic..."
- "Couldn't reach Epic. Check your connection."

### 10.3 Standard microcopy

| Context | Copy |
|---|---|
| Save indicator | "Saved" (1.5s, no icon) |
| Generic loading | "Loading…" |
| Long operation | "[Verb]ing X of Y [thing]…" with progress |
| Empty primary | Action-oriented, not negative — "Add your first record" not "No records yet" |
| Success toast | "[Action] saved." (past tense, no exclamation) |
| Error toast | "Couldn't [verb]. [Specific reason if known]." |
| Destructive confirm | "Revoke access to Dr. Martinez? They won't be able to view your record anymore." |
| Optional field | "Optional" (plain text, never "(Optional)" with parens) |
| Required field | Asterisk + "Required" in `aria-label`, no "(Required)" text |

---

## 11. Motion & Animation

**Default: no motion.** Add motion only when it serves comprehension.

### 11.1 When motion is allowed

- **Page transitions:** subtle fade (200ms ease-out), only between sibling routes
- **Micro-interactions:** button press (100ms), checkbox toggle (150ms), select expand (200ms)
- **Progress feedback:** linear progress bar fills in real time, circular for indeterminate
- **State changes:** toast slide-in (300ms), modal fade-in (250ms)
- **Data updates:** number tickers when a value changes (400ms count-up)
- **QR scan line:** 2-second loop, ease-in-out, very subtle

### 11.2 When motion is forbidden

- Decorative animations (floating icons, background blobs)
- Auto-playing carousels
- Long animations (> 500ms) for primary interactions
- Animations that block input
- Spring physics that overshoot (bouncy modals)
- Parallax scrolling
- Hover animations on touch devices

### 11.3 Reduced motion

`@media (prefers-reduced-motion: reduce)` disables ALL non-essential animations. Only critical state changes (loading indicators, progress bars) remain. Tested by enabling "Reduce Motion" in OS settings.

---

## 12. Anti-Patterns to Avoid

The 13 things this app must never look like.

1. **Generic SaaS hero** with "Welcome to HealthKey, your all-in-one [...]"
2. **3-column feature grid** with icons in colored circles, repeated symmetrically
3. **Purple/violet/indigo gradients** anywhere
4. **Centered everything** — heading, body, button, all centered for no reason
5. **Decorative icons in colored circles** as section dividers
6. **Wavy SVG dividers** between sections
7. **Cookie-cutter section rhythm** (hero → 3 features → testimonial → CTA)
8. **Floating decorative blobs** in the background
9. **Emoji as design elements** — rockets in headings, emoji bullets
10. **Colored left-border on cards** (`border-left: 3px solid <accent>`)
11. **Modal dialogs as primary navigation** — modals are for confirmation, not flow
12. **Card mosaic dashboards** — 12 colored cards with vague metrics
13. **Marketing language inside the app** — "Unlock the power of...", "Boost your...", "Your all-in-one..."

If the design ever drifts toward any of these, stop and rebuild. None of these serves a stressed patient looking for their lab results.

---

## Appendix A — Implementation Checklist

When implementing each screen, verify:

- [ ] All 5 interaction states designed (loading, empty, error, success, partial)
- [ ] Mobile (375px), tablet (768px), desktop (1280px) layouts specified
- [ ] Keyboard navigation works without a mouse
- [ ] Screen reader announces all dynamic changes
- [ ] Color contrast verified with axe-core or Lighthouse
- [ ] No hardcoded colors; all use design tokens
- [ ] Plain-language copy reviewed (no clinical jargon without tooltips)
- [ ] Auto-save where applicable; no "Save" button on PATCHable forms
- [ ] DataSourceBadge present on all health data
- [ ] Empty state has warmth, primary action, context
- [ ] Error state has plain language, retry, no blame
- [ ] Touch targets ≥ 44px, spacing ≥ 8px
- [ ] Reduced motion respected
- [ ] No anti-patterns from §12

---

## Appendix B — Component → Screen Map

| Component | Used in screens |
|---|---|
| `OnboardingStepShell` | All `/onboarding/*` |
| `ThreeModeInput` | Conditions, Lifestyle, Family, Disease, Labs onboarding steps |
| `CompletenessIndicator` | Onboarding summary, Dashboard home |
| `DataSourceBadge` | Records (every value), Lab cards, Provider view |
| `LabValueCard` | Records tab labs section, Dashboard home labs |
| `LabTrendChart` | `/dashboard/records/labs/{field}` |
| `ConflictResolutionCard` | `/dashboard/records/conflicts` |
| `AccessGrantCard` | Share tab, active grants |
| `QRCodeModal` | Share tab "View QR" action |
| `DiseaseProfileTab` | `/onboarding/disease`, Records tab disease section |
| `TimelineEntry` | `/dashboard/records/timeline` |

---

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 1 | CLEAR (main, 2026-04-03) | 6 scope proposals, all accepted |
| Codex Review | `/codex review` | Independent 2nd opinion | 0 | — | — |
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 2 | CLEAR (PLAN) | ZK relaxed, researcher API added |
| Design Review | `/plan-design-review` | UI/UX gaps | 1 | CLEAR (PLAN) | design system, 13 screens, 5 states each, a11y, journey, anti-patterns |
| DX Review | `/plan-devex-review` | Developer experience gaps | 0 | — | — |

**VERDICT:** ENG + DESIGN CLEAR — patient app design document created. Implementation can begin Phase 1 (auth + onboarding) with the screen wireframes in §5 and component library in §4.
