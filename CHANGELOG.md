# Changelog

## Lab editor + trend chart polish + detail UX (2026-04-15)

A round of polish on top of the lab trend detail route: per-row editing, a better chart, a proper sparkline, a colored trend badge, and a few UX knots straightened out.

### Backend

- **PATCH `/api/v1/labs/results/{id}/`** — new endpoint to edit an existing result. `LabResultUpdateSerializer` mirrors create's validation + unit normalisation but `test_type_id` is immutable on update (attempt to change it is silently dropped; backend keeps the original test). Shared helpers `_validate_value_fields` and `_apply_normalised_fields` are extracted from the create path so create and update go through the same unit-conversion + reference-range logic — no drift.
- **Provenance preserved on update**: `source`, `match_method`, and `confidence` are left alone. A manually-edited document-extracted row keeps its origin trail.
- **7 new API tests** covering PATCH value, PATCH unit triggers re-normalization, PATCH date only, PATCH overrides catalog range with report range, PATCH other user's result → 404, PATCH incompatible unit → 400, PATCH `test_type_id` in body silently ignored. **73 tests passing.**

### Trend chart (`LabTrendChart`)

- `LineChart` → `AreaChart` with a vertical gradient fill (brand-blue @ 25% → 2% opacity). The area is clipped by the curve, not a rectangle — actual "area under the curve."
- Reference range: rectangular `ReferenceArea` replaced with two horizontal dashed `ReferenceLine`s. Colour switched from green to neutral `muted-foreground` so they stop blending into the gradient fill; full opacity, 1.5px thick, `strokeDasharray="4 3"`. Numeric bounds moved to a legend caption **above** the chart with a matching dashed swatch, so they stay readable without competing with the plot.
- Data points rendered as `r=5` filled circles with a `hsl(var(--background))` ring so they pop against both the curve and the fill. Hover `activeDot` grows to `r=7`.
- Tooltip: cursor dashed guide line, full-date label (`"March 15, 2026"` via `labelFormatter` reading the raw ISO `date` from the payload), value + unit. Tooltip style tightened (6/10px padding, semibold label).
- Plot area left-aligned: `margin.left = -24` pulls the YAxis labels into the container's padding so the curve starts flush with the card edge. `XAxis padding={{ left: 8, right: 8 }}` keeps the first/last dots from clipping.

### `LabValueCard` on the Records tab

- **Sparkline rebuilt.** Stretches to fill the card width (`preserveAspectRatio="none"`). Data points are now **HTML `<div>`s** absolutely positioned over the polyline SVG — CSS `border-radius` circles stay perfectly round regardless of the container's aspect ratio, unlike SVG `<circle>`s which deform into ellipses under non-uniform scaling. Each dot has `onPointerEnter`/`Leave` gated to `pointerType === "mouse"` (mobile taps fall through to the parent `<Link>`). Tooltip pops above the hovered dot showing value + unit + short date.
- **Sparkline height bumped to `h-12`** (48px) so the trend shape is more pronounced.
- **Layout restructured.** Value + unit stacked on top of "Normal: X–Y" caption, both on the left. Sparkline taller and right-aligned, vertically centered so it spans both text lines. `items-center` on the row keeps alignment consistent.
- **"No range" placeholder.** When a test has no reference range (`M-spike`, qualitative infection screens after `value_type` filter), the "Normal: …" slot shows an italic `No range` label instead of collapsing. All cards now end up the same height regardless of whether the test has a range, so the grid on Records stays flush.
- **Deduped "No range" label.** `StatusChip` used to show "No range" for `status === "unknown"`, which duplicated the placeholder on the range line. Now `StatusChip` returns null for unknown — the range slot is the single source of truth.
- **`TrendBadge`** replaces the bare muted arrow. Coloured pill showing the signed delta (`+0.7`, `−1.2`, `±0`) and a direction arrow. Colour tone is computed from **distance-to-reference-range** (closer → improving/green, farther → worsening/amber, equal → stable/gray) — not naive up/down, because "up is good" isn't universal (cholesterol vs hemoglobin). Native `title` tooltip explains the tone; `aria-label` gives screen readers the full delta.
- **Header truncation fix.** Long test names like "Absolute neutrophil count" no longer push the trend badge off the card on narrow widths. `h3` uses `min-w-0 truncate`; badge + chevron stay `shrink-0`.

### `LabTrendDetail` page

- **Edit button on every history row.** Pencil icon next to the trash opens `LabManualEntryDialog` in edit mode pre-filled with the row's values.
- **Chart hidden for qualitative tests.** On `/dashboard/records/labs/hbsag` (and the other three qualitative infection screens) the chart card is skipped entirely — trends don't apply to reactive/non-reactive results. The history list still shows every measurement. No misleading "No data yet" card.

### `LabManualEntryDialog` editor upgrade

- **Edit mode.** New optional `editingResult?: LabResult` prop. When set, the dialog title becomes "Edit lab result", the test selector is locked, and the form is pre-filled from `source_text` / `source_unit` (the verbatim original input, not the normalised value — so editing a row entered as `125 g/L` shows `125 g/L` again, not `12.5 g/dL`). Submit button toggles between "Save result" / "Update result".
- **`useUpdateLabResult()`** hook invalidates the shared `["labs", "results"]` query key so the chart, sparkline on Records, and history list all re-render after save.
- **Atomic form initialization.** Merged the hydration effect and the "preselect defaultTestAbbrev" effect into a single `reset()` call. Previously a race between the two could briefly show an empty selector or drop the pre-selection; now the dialog opens with the test, unit, and date all populated in one atomic state update.
- **Test selector locked when opened from a detail page.** `disabled` on the Select is now `isEditing || Boolean(defaultTestAbbrev)` — clicking Add on `/dashboard/records/labs/hgb` opens the dialog with Hemoglobin pre-selected AND locked, so users can't accidentally file the new row under a different test. The Records tab's main "Add lab result" button still opens the dropdown unlocked for free-form test selection.
- **Controlled qualitative Select.** The "Result" dropdown for qualitative tests (HIV, HBsAg, HCV) was uncontrolled — editing an existing row showed the placeholder instead of the stored value, even though saving worked. Added `value={watch("value_qualitative") || undefined}` so Radix reads from the form state. Editing now shows the current stored result pre-selected throughout the dialog lifecycle.

## Lab trend detail route + bundle cleanup (2026-04-15)

- **New route** `/dashboard/records/labs/:abbreviation` → `LabTrendDetail` page with back link, test header, full-width `LabTrendChart` (line + reference band + status-coloured dots), and a chronological history list with per-row delete button. Opens the manual entry dialog pre-selected to the current test when the patient taps "Add"
- **`LabValueCard` is now a `<Link>`** wrapping the whole card. Tapping any value card on Records navigates to its trend detail. Subtle `hover:bg-muted/30` and a trailing chevron hint at the affordance without turning it into a loud primary action
- **Code-split the detail route** with `React.lazy` + `Suspense` because it pulls in recharts. Main bundle dropped from **805 KB → 66 KB** (gz 18 KB). Recharts now loads only when the user opens a trend
- **Delete flow**: history list row's trash button calls `useDeleteLabResult()`, which invalidates the `labs.results` query so the chart, sparkline on Records, and the history list all re-render after removal. Browser `confirm()` gates the action in Phase 2a; a proper shadcn `AlertDialog` is a minor follow-up
- **`.gitignore`** now ignores `frontend/tsconfig.tsbuildinfo` (TypeScript incremental build cache — regenerated on every `tsc -b`). Untracked via `git rm --cached`

## Regional units + per-unit ranges & placeholders (2026-04-15)

Incremental UX improvements on top of Phase 2a so patients outside the US can enter values in the units their lab reports actually print.

### Alternative units per test (US / UK / EU)

- New `LabTestType.alternative_units` JSONField + migration
- Seeded in the fixture for every test where the alt exists: CBC counts (`K/uL`, `10^9/L`), hemoglobin + albumin + M-spike (`g/L`), creatinine + bilirubin (`µmol/L`), calcium + LDL + HDL (`mmol/L`), AST/ALT/ALP/LDH (`IU/L`), TSH (`µIU/mL`), β2-microglobulin (`µg/mL`, `ng/mL`)
- `unit_converter.py` — defined `mIU` and `uIU` as proper pint units (fixed silent TSH conversion failure)
- LDL/HDL molecular weights (386.65 g/mol) added so mg/dL ↔ mmol/L round-trips via the molar bridge
- Manual entry dialog's unit field is now a `Select` populated from `[default_unit, ...alternative_units]` with the default marked. Tests without alternatives show a read-only unit label
- +10 regression tests covering every regional alt-unit round-trip

### Per-unit placeholders (`sample_values`)

- New `LabTestType.sample_values` JSONField + migration — shape `{"unit": "display_value"}`
- Seeded from the fixture; realistic magnitudes per test × per unit (e.g. hemoglobin `{"g/dL": "14.0", "g/L": "140"}`)
- `LabManualEntryDialog` input placeholder is driven entirely from the catalog — no UI-side lookup table, no domain knowledge in the frontend
- Fixture invariant test: every numeric test's `sample_values` must cover `default_unit + alternative_units`. CI fails if a new alt unit ships without a sample

### Per-unit reference ranges (`reference_ranges_by_unit`)

- `LabTestTypeSerializer.reference_ranges_by_unit` — a new `SerializerMethodField` that pre-computes the catalog's default range in every supported unit using the same `unit_converter.normalise()` that runs on save
- No migration; computed at serialization time from existing fields
- `LabManualEntryDialog` displays **"Normal range: X–Y unit"** below the value input, tracking the currently selected unit in real time. Switching hemoglobin from `g/dL` to `g/L` flips `12.0–17.5` to `120–175`
- Graceful skip when conversion fails or a qualitative test has no range — the "Normal range:" line simply doesn't render rather than showing misleading numbers
- +4 tests including the invariant that every numeric test with a default range covers both the default and every alternative

### Misc

- **`select` empty-value bug**: Radix `Select` forbids `""` as an item value; the cancer diagnosis selector in onboarding now maps the empty "None" option to a `_none_` sentinel at the boundary
- **Matrix layout**: family history grid uses CSS grid with `minmax(86px, 1.4fr) repeat(5, minmax(50px, 1fr))` so it fits iPhone SE (375px) without horizontal scroll; "Maternal grandparent" abbreviated to "Maternal GP" with full text in aria-label + title, footnote below the table spelling out `* GP — grandparent`
- **Dark mode**: inline `<script>` in `index.html` applies `class="dark"` on `<html>` before React mounts, based on `prefers-color-scheme` with a `hk_theme` localStorage override. Lives with a `matchMedia` listener for live OS theme toggles
- **API proxy**: `vite.config.ts` calls `dns.setDefaultResultOrder("ipv4first")` so `localhost` resolves to `127.0.0.1` instead of `::1` (Django dev server only binds IPv4)
- **Tailwind-merge custom classes**: `cn()` uses `extendTailwindMerge` with the custom font-size and `healthkey-*` color groups so the Button's `text-white` isn't silently stripped when colliding with `text-body-lg` from the `size="lg"` variant
- **Login button**: replaced generic shadcn `text-white` with the `healthkey.text-white` token to match the cancerbot/ui.v2 reference

Tests: **66 passing** (backend labs app, up from 56 end of Phase 2a scaffold).

## Phase 2a — Labs catalog + manual entry (2026-04-15)

### What works end-to-end right now

1. Sign in → Records tab → "Add lab result"
2. Pick any of 37 tests from a grouped dropdown
3. Type a value + optional unit (e.g. creatinine in µmol/L)
4. Save → backend normalises to default unit, computes status, returns 201
5. Records tab immediately shows a `LabValueCard` with the new value, reference range, sparkline (single dot if one value), and status chip
6. Add a second measurement of the same test → sparkline grows, trend arrow appears
7. Delete the account → cascade wipes all `LabResult` rows via the `User` FK

### What's deliberately not yet implemented (Phase 2b–d)

- File upload (`LabUpload` / `LabUploadFile` models, `POST /uploads/`) — **Phase 2b**
- PDF rasterization + LLM vision extraction — **Phase 2c**
- Tiered matching (`matching.py` with LOINC → exact → fuzzy → disambiguation) — **Phase 2c**
- Review screen + commit endpoint — **Phase 2d**
- Full `LabTrendChart` route page at `/dashboard/records/labs/{abbrev}` — minor, just needs a route and nav

### Known trade-offs & follow-ups worth flagging

1. **`LabResult.upload_id` is a plain `PositiveIntegerField`**, not a real FK. Phase 2b will replace it with a real `ForeignKey(LabUpload)` via a migration. I left it as a placeholder so Phase 2a's migration doesn't depend on a model that doesn't exist yet. The FK backfill is a 2-minute migration when 2b lands.
2. **Audit pseudonymization is a log-only stub.** The real audit app doesn't exist yet. When it does, swap the `logger.info` in `signals.py` for the `AuditLog.objects.filter(...).update(actor_id=None, resource_id=None)` call. The hook is wired so the contract is findable.
3. **Manual entry has no trend chart route yet.** `LabTrendChart` is imported but not reachable from nav. Simplest add: a new route `/dashboard/records/labs/:testAbbrev` pointing at a `LabTrendDetailPage`. Can land in its own tiny PR.
4. **`select_related` on the ViewSet uses the default paginator** (50 per page from `PAGE_SIZE` in settings). At Phase 2a scale that's fine; if a patient has years of daily measurements we'll revisit.
5. **No status filter on the list endpoint** — only `test`, `from`, `to`. Adding `?status=above` is trivial if the UI needs it.

**Next step:** Phase 2b (upload + storage) or a small follow-up to ship the trend chart route? Either is ~30 min of work.
