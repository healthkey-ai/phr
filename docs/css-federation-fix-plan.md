# Fix: CSS Variable Loss in Federated Modules

## Problem

Federated lab components lose CSS variables when rendered in the host app. Three root causes:

### 1. Blanket `:root` rewriting (`injectStyles.ts:18`)

```ts
rest = rest.replace(/:root/g, ".hk-labs-root");
```

Vite compiles `labs.css` through Tailwind v4 before the `?inline` import returns it as a string. The compiled output contains multiple `:root` selectors — Tailwind's preflight, `@property` rules, theme variable emissions, and the explicit `@layer remote-defaults` fallbacks. Replacing all of them with `.hk-labs-root` breaks Tailwind's generated CSS.

### 2. Remote `@theme` references host variable names directly (`labs.css:63-85`)

```css
/* labs.css */
@theme inline {
  --color-healthkey-bg-primary: hsl(var(--app-bg-primary));  /* host internal name */
}
```

This couples the remote build to the host's internal variable namespace. Both repos must stay exactly in sync, and there is no explicit contract boundary.

### 3. Portal breakout

`LabUploadDialog.tsx` and `LabManualEntryDialog.tsx` use Radix `Dialog.Portal` and `Select.Portal`, which render at `document.body`. Portaled elements are outside `.hk-labs-root` and lose any variables scoped there.

## Solution

### Design: `--hk-labs-*` contract namespace on `:root`

Introduce a remote-owned `--hk-labs-*` token contract. Define fallbacks on `:root` inside `@layer theme` (low specificity). The host overrides them on `:root` unlayered (always wins). Since `--hk-labs-*` is a unique namespace, `:root` is safe — no conflict with host tokens, and portaled elements inherit automatically.

```
Remote defines:   @layer theme { :root { --hk-labs-bg-primary: 0 0% 100%; } }
Host overrides:   :root { --hk-labs-bg-primary: var(--app-bg-primary, 0 0% 100%); }
Theme uses:       @theme inline { --color-healthkey-bg-primary: hsl(var(--hk-labs-bg-primary)); }
Components use:   className="bg-healthkey-bg-primary"
```

The `.hk-labs-root` class stays only for component-level presentation (font-family, color) in `@layer components`, not for token scoping.

### `--hk-labs-*` is a global public contract

Since `--hk-labs-*` lives on `:root`, it becomes a global integration API. Rules:

- The remote consumes `--hk-labs-*` variables. It must not consume `--app-*`, `--brand-*`, `--text-*` or other host internals directly.
- The host may override `--hk-labs-*` globally on `:root`.
- The remote must provide standalone fallback values for all `--hk-labs-*` tokens.
- Per-instance theming (multiple differently-themed remotes on one page) would require portal containers instead. Not needed now.

### Why `@theme inline`

`@theme inline` is correct here because the generated utility resolves directly through
the runtime variable supplied by the host:

```css
.bg-healthkey-bg-primary {
  background-color: hsl(var(--hk-labs-bg-primary));
}
```

Without `inline`, Tailwind can emit indirection that resolves differently depending on
where variables are defined.

## Changes

### Step 1: Introduce `--hk-labs-*` contract in `labs.css`

**File: `frontend/src/federation/labs.css`**

Replace `@theme inline` host-variable references with `--hk-labs-*` contract tokens:

```css
/* Before */
@theme inline {
  --color-healthkey-bg-primary: hsl(var(--app-bg-primary));
  --color-healthkey-text-primary: hsl(var(--text-primary-900));
  --color-healthkey-brand-700: hsl(var(--brand-700));
  /* ... */
}

/* After */
@theme inline {
  --color-healthkey-bg-primary: hsl(var(--hk-labs-bg-primary));
  --color-healthkey-text-primary: hsl(var(--hk-labs-text-primary));
  --color-healthkey-brand-700: hsl(var(--hk-labs-brand-700));
  /* ... */
}
```

Replace `@layer remote-defaults { :root { ... } }` with `@layer theme { :root { ... } }` containing only `--hk-labs-*` tokens:

```css
/* Before — generic host variable names on :root */
@layer remote-defaults {
  :root {
    --app-bg-primary: 0 0% 100%;
    --text-primary-900: 216 17% 14%;
    --brand-700: 212 87% 33%;
    /* 50+ variables with host-internal names */
  }
}

/* After — namespaced contract tokens on :root */
@layer theme {
  :root {
    --hk-labs-bg-primary: 0 0% 100%;
    --hk-labs-bg-secondary: 0 0% 98%;
    --hk-labs-bg-active: 0 0% 98%;
    --hk-labs-text-primary: 216 17% 14%;
    --hk-labs-text-secondary: 220 9% 32%;
    --hk-labs-text-tertiary: 218 8% 46%;
    --hk-labs-text-disabled: 0 0% 83%;
    --hk-labs-text-brand: 212 87% 33%;
    --hk-labs-text-white: 0 0% 100%;
    --hk-labs-border-secondary: 0 0% 91.4%;
    --hk-labs-gray-50: 0 0% 98%;
    --hk-labs-gray-100: 0 0% 96%;
    --hk-labs-gray-200: 0 0% 91.4%;
    --hk-labs-gray-700: 220 9% 32%;
    --hk-labs-brand-25: 199 100% 97%;
    --hk-labs-brand-50: 199 100% 92%;
    --hk-labs-brand-200: 199 100% 64%;
    --hk-labs-brand-700: 212 87% 33%;
    --hk-labs-brand-alt: 212 95% 40%;
    --hk-labs-brand-green: 146 70% 45%;
    --hk-labs-link-primary: 212 95% 40%;
    --hk-labs-link-hover: 212 87% 33%;
    --hk-labs-success-50: 152 88% 95%;
    --hk-labs-success-200: 152 68% 81%;
    --hk-labs-success-700: 152 91% 29%;
    --hk-labs-warning-50: 48 100% 96%;
    --hk-labs-warning-200: 43 98% 77%;
    --hk-labs-warning-700: 25 95% 37%;
    --hk-labs-error-50: 4 86% 97%;
    --hk-labs-error-200: 5 86% 89%;
    --hk-labs-error-700: 5 79% 40%;
    --hk-labs-radius: 0.5rem;
  }
}
```

#### Shadcn token handling

Before removing shadcn tokens (`--background`, `--foreground`, `--card`, etc.) from the remote, audit whether remote `components/ui/*` still uses classes like `bg-background`, `text-foreground`, `border-border`. If they do, keep temporary shadcn aliases mapped through `--hk-labs-*` (not host internals):

```css
/* Temporary compatibility bridge — remove once components are migrated */
@theme inline {
  --color-background: hsl(var(--hk-labs-bg-primary));
  --color-foreground: hsl(var(--hk-labs-text-primary));
  --color-card: hsl(var(--hk-labs-bg-primary));
  --color-card-foreground: hsl(var(--hk-labs-text-primary));
  --color-popover: hsl(var(--hk-labs-bg-primary));
  --color-popover-foreground: hsl(var(--hk-labs-text-primary));
  --color-muted: hsl(var(--hk-labs-gray-100));
  --color-muted-foreground: hsl(var(--hk-labs-text-tertiary));
  --color-accent: hsl(var(--hk-labs-gray-100));
  --color-accent-foreground: hsl(var(--hk-labs-text-primary));
  --color-border: hsl(var(--hk-labs-border-secondary));
  --color-input: hsl(var(--hk-labs-border-secondary));
  --color-ring: hsl(var(--hk-labs-brand-700));
  --color-destructive: hsl(var(--hk-labs-error-700));
  --color-destructive-foreground: hsl(var(--hk-labs-text-white));
  --color-primary: hsl(var(--hk-labs-brand-700));
  --color-primary-foreground: hsl(var(--hk-labs-text-white));
  --color-secondary: hsl(var(--hk-labs-gray-100));
  --color-secondary-foreground: hsl(var(--hk-labs-text-primary));
}
```

Preferred long-term: migrate remote UI classes to HealthKey tokens (`bg-background` -> `bg-healthkey-bg-primary`), then remove the compatibility bridge.

### Step 2: Remove `:root` rewriting in `injectStyles.ts`

**File: `frontend/src/federation/injectStyles.ts`**

Delete the `:root` replacement (lines 15-18). Also simplify by removing the `@import` extraction unless it is specifically needed for font load ordering:

```ts
/* Before */
import css from "./labs.css?inline";

let injected = false;

export function injectStyles() {
  if (injected) return;
  injected = true;

  const imports: string[] = [];
  let rest = css.replace(
    /@import\s+(?:url\([^)]+\)|"[^"]+"|'[^']+')\s*;?/g,
    (match) => { imports.push(match); return ""; },
  );

  rest = rest.replace(/:root/g, ".hk-labs-root");

  if (imports.length > 0) {
    const fontStyle = document.createElement("style");
    fontStyle.setAttribute("data-mf", "labs-remote-fonts");
    fontStyle.textContent = imports.join("\n");
    document.head.appendChild(fontStyle);
  }

  const style = document.createElement("style");
  style.setAttribute("data-mf", "labs-remote");
  style.textContent = rest;
  document.head.appendChild(style);
}

/* After */
import css from "./labs.css?inline";

let injected = false;

export function injectStyles() {
  if (injected) return;
  injected = true;

  const style = document.createElement("style");
  style.setAttribute("data-mf", "labs-remote");
  style.textContent = css;
  document.head.appendChild(style);
}
```

If `@import` extraction is needed for browser compatibility, keep it — but do not otherwise mutate the Tailwind output.

### Step 3: Add host-side token bridge in `index.css`

**File: `frontend/src/index.css`**

Add at the end of the file, outside any `@layer`. Every `var()` call includes a hardcoded
fallback so the remote survives if host and remote deploy out of sync:

```css
:root {
  --hk-labs-bg-primary: var(--app-bg-primary, 0 0% 100%);
  --hk-labs-bg-secondary: var(--app-bg-secondary, 0 0% 98%);
  --hk-labs-bg-active: var(--app-bg-active, 0 0% 98%);

  --hk-labs-text-primary: var(--text-primary-900, 216 17% 14%);
  --hk-labs-text-secondary: var(--text-secondary-700, 220 9% 32%);
  --hk-labs-text-tertiary: var(--text-quaternary-500, 218 8% 46%);
  --hk-labs-text-disabled: var(--text-disabled, 0 0% 83%);
  --hk-labs-text-brand: var(--text-brand-secondary-700, 212 87% 33%);
  --hk-labs-text-white: var(--text-white, 0 0% 100%);

  --hk-labs-border-secondary: var(--border-secondary, 0 0% 91.4%);

  --hk-labs-gray-50: var(--gray-50, 0 0% 98%);
  --hk-labs-gray-100: var(--gray-100, 0 0% 96%);
  --hk-labs-gray-200: var(--gray-200, 0 0% 91.4%);
  --hk-labs-gray-700: var(--gray-700, 220 9% 32%);

  --hk-labs-brand-25: var(--brand-25, 199 100% 97%);
  --hk-labs-brand-50: var(--brand-50, 199 100% 92%);
  --hk-labs-brand-200: var(--brand-200, 199 100% 64%);
  --hk-labs-brand-700: var(--brand-700, 212 87% 33%);
  --hk-labs-brand-alt: var(--brand-primary-alt, 212 95% 40%);
  --hk-labs-brand-green: var(--brand-green-500, 146 70% 45%);

  --hk-labs-link-primary: var(--link-primary, 212 95% 40%);
  --hk-labs-link-hover: var(--link-primary-hover, 212 87% 33%);

  --hk-labs-success-50: var(--success-50, 152 88% 95%);
  --hk-labs-success-200: var(--success-200, 152 68% 81%);
  --hk-labs-success-700: var(--success-700, 152 91% 29%);

  --hk-labs-warning-50: var(--warning-50, 48 100% 96%);
  --hk-labs-warning-200: var(--warning-200, 43 98% 77%);
  --hk-labs-warning-700: var(--warning-700, 25 95% 37%);

  --hk-labs-error-50: var(--error-50, 4 86% 97%);
  --hk-labs-error-200: var(--error-200, 5 86% 89%);
  --hk-labs-error-700: var(--error-700, 5 79% 40%);

  --hk-labs-radius: var(--radius, 0.5rem);
}
```

Being unlayered, these override the `@layer theme` fallbacks in `labs.css`. Dark mode works automatically because the host's `.dark` block already switches `--app-bg-primary`, `--brand-700`, etc.

The hardcoded fallback values match the remote's standalone defaults. If the host is missing a token (e.g. during an out-of-sync deploy), the remote renders with its own defaults instead of breaking.

### Step 4: Add dev-only token diagnostic

**File: `frontend/src/federation/assertLabsTokens.ts` (new)**

```ts
export function assertLabsTokens() {
  if (import.meta.env.PROD) return;

  const root = getComputedStyle(document.documentElement);

  const required = [
    "--hk-labs-bg-primary",
    "--hk-labs-bg-secondary",
    "--hk-labs-text-primary",
    "--hk-labs-text-secondary",
    "--hk-labs-text-brand",
    "--hk-labs-border-secondary",
    "--hk-labs-brand-25",
    "--hk-labs-brand-50",
    "--hk-labs-brand-200",
    "--hk-labs-brand-700",
    "--hk-labs-radius",
  ];

  const missing = required.filter((t) => !root.getPropertyValue(t).trim());

  if (missing.length > 0) {
    console.warn("[labs-remote] Missing CSS tokens:", missing);
  }
}
```

Call from `LabsProvider.tsx` after style injection.

## Execution order

Steps 1 + 2 + 3 form one atomic change — they must ship together.
Step 4 can ship in the same PR or independently.

## Follow-up (separate PRs)

### Tailwind prefix for remote

Add `prefix(hk)` to prevent utility class collisions between host and remote:

```css
@import "tailwindcss" prefix(hk-labs);
```

Then update all lab component class names: `bg-healthkey-bg-primary` becomes `hk-labs:bg-healthkey-bg-primary`. High effort, deferred.

### Migrate remote shadcn classes

Replace `bg-background`, `text-foreground`, `border-border` etc. in remote `components/ui/*` with `bg-healthkey-bg-primary`, `text-healthkey-text-primary`, `border-healthkey-border-secondary`. Then remove the temporary shadcn compatibility bridge from `@theme inline`.

### Portal containers for per-instance theming

If the app ever needs multiple differently-themed lab remotes on one page, switch from global `:root` `--hk-labs-*` to per-instance portal containers passed through context. Not needed now.

## Verification checklist

- [ ] Standalone dev harness (`vite.remote.config.ts`): colors, radius, typography resolve correctly
- [ ] Host app: remote components pick up host brand tokens
- [ ] Dark mode: tokens switch in both standalone and host
- [ ] `LabUploadDialog` (portaled): correct colors/radius when open
- [ ] `LabManualEntryDialog` Select dropdown (portaled): correct colors when open
- [ ] No `--app-*` or `--text-primary-900` etc. referenced anywhere in `labs.css` after changes
- [ ] `injectStyles.ts` has no `:root` rewriting
- [ ] Search remote TSX for `bg-background`, `text-foreground`, `border-border`, `ring-ring`, `bg-card`, `text-muted-foreground` — either migrate or confirm shadcn bridge covers them
- [ ] Test missing host token fallback by temporarily removing one host token
- [ ] Test CSS load order: remote CSS before host CSS and host CSS before remote CSS
- [ ] Test production build, not only dev
