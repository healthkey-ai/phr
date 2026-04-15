# Changelog

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
