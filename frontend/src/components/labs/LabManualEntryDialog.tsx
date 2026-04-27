/**
 * LabManualEntryDialog — Type-in flow for a single lab value.
 * Phase 2a scope: no file upload, no extraction. That's Phase 2b-d.
 *
 * Validates client-side that the chosen test exists in the catalog, then
 * POSTs to /labs/results/. Backend does unit normalisation + status calc.
 */
import { useEffect, useMemo, useState } from "react";
import type { UseFormRegister } from "react-hook-form";
import { useForm } from "react-hook-form";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  useCatalog,
  useCreateLabResult,
  useUpdateLabResult,
} from "@/features/labs/api";
import type { LabTestEntry, LabValue } from "@/types/labs";

/** Fallback placeholder when the backend catalog doesn't supply one. */
const GENERIC_PLACEHOLDER = "e.g. 12.5";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Pre-select a test by abbreviation (e.g. opening from a specific card). */
  defaultTestAbbrev?: string;
  /**
   * When set, the dialog switches to edit mode:
   *   - Title becomes "Edit lab result"
   *   - Test selector is locked (test_type is immutable server-side too)
   *   - Fields are pre-filled from the stored result's source_text / source_unit
   *   - Submit calls PATCH /labs/results/{id}/ instead of POST
   */
  editingResult?: LabValue | null;
}

interface FormValues {
  test_type_id: string; // Select gives us strings
  value: string;
  value_qualitative: string;
  unit: string;
  measured_at: string;
}

export function LabManualEntryDialog({
  open,
  onOpenChange,
  defaultTestAbbrev,
  editingResult,
}: Props) {
  const { data: catalog } = useCatalog();
  const create = useCreateLabResult();
  const update = useUpdateLabResult();
  const [serverError, setServerError] = useState<string | null>(null);

  const isEditing = Boolean(editingResult);

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({
    defaultValues: {
      test_type_id: "",
      value: "",
      value_qualitative: "",
      unit: "",
      measured_at: new Date().toISOString().slice(0, 10),
    },
  });

  /**
   * Atomic form initialisation on dialog open.
   *
   * Handles three cases in a single `reset()`:
   *   1. Edit mode     → hydrate from editingResult's source_text/source_unit
   *                      (the verbatim original input, not the normalised
   *                      value — e.g. "125 g/L" for hemoglobin, not "12.5 g/dL")
   *   2. Create mode with defaultTestAbbrev → pre-select that test in the
   *      catalog and its default_unit in one shot (e.g. clicking "Add" on
   *      /dashboard/records/labs/hgb lands the dialog on Hemoglobin · g/dL)
   *   3. Create mode with nothing           → empty form, user picks a test
   *
   * Consolidating into a single effect avoids a two-render race where a
   * separate "preselect" effect would fire AFTER the reset, briefly showing
   * an empty selector and occasionally dropping the preselection.
   */
  useEffect(() => {
    if (!open) return;
    if (editingResult) {
      reset({
        test_type_id: String(editingResult.test.id),
        value: editingResult.source_text ?? "",
        value_qualitative:
          editingResult.test.value_type === "qualitative"
            ? editingResult.source_text ?? ""
            : "",
        unit: editingResult.source_unit || editingResult.unit || "",
        measured_at:
          editingResult.measured_at ??
          editingResult.created_at.slice(0, 10),
      });
    } else {
      // Create mode — look up the default test (if any) in the catalog so
      // the selector + unit are set in the same reset as everything else.
      const defaultTest =
        defaultTestAbbrev && catalog
          ? catalog.tests.find((t) => t.abbreviation === defaultTestAbbrev)
          : undefined;
      reset({
        test_type_id: defaultTest ? String(defaultTest.id) : "",
        value: "",
        value_qualitative: "",
        unit: defaultTest?.default_unit ?? "",
        measured_at: new Date().toISOString().slice(0, 10),
      });
    }
    setServerError(null);
  }, [open, editingResult, reset, defaultTestAbbrev, catalog]);

  // Group tests by category for a sensible Select
  const categoriesWithTests = useMemo(() => {
    if (!catalog) return [];
    const catMap = new Map<string, { key: string; name: string; tests: LabTestEntry[] }>();
    for (const t of catalog.tests) {
      const key = t.category || "other";
      if (!catMap.has(key)) {
        catMap.set(key, { key, name: key, tests: [] });
      }
      catMap.get(key)!.tests.push(t);
    }
    return Array.from(catMap.values()).filter((c) => c.tests.length > 0);
  }, [catalog]);

  const selectedTestId = watch("test_type_id");
  const selectedTest: LabTestEntry | undefined = useMemo(() => {
    if (!catalog || !selectedTestId) return undefined;
    return catalog.tests.find((t) => String(t.id) === selectedTestId);
  }, [catalog, selectedTestId]);

  // When the user manually changes the test in CREATE mode, default the unit
  // to the new test's default_unit. The initial preselect (via the hydration
  // effect above) also sets the unit, so this effect mainly matters when the
  // user picks a different test from the dropdown mid-flow.
  //
  // Guarded on isEditing because in edit mode the test selector is disabled
  // and the unit came from the stored source_unit, which we don't want to
  // stomp on.
  useEffect(() => {
    if (isEditing) return;
    if (selectedTest) {
      setValue("unit", selectedTest.default_unit, { shouldValidate: false });
    }
  }, [selectedTest?.id, setValue, isEditing]); // eslint-disable-line react-hooks/exhaustive-deps

  const isQualitative = selectedTest?.value_type === "qualitative";

  // Lock the test selector when:
  //   - editing an existing row (backend rejects test_type changes anyway), OR
  //   - opened from a test-specific page via defaultTestAbbrev (the caller's
  //     intent is "add a measurement for THIS test", not "pick one")
  const testSelectorLocked = isEditing || Boolean(defaultTestAbbrev);

  const onSubmit = async (values: FormValues) => {
    setServerError(null);
    if (!selectedTest) {
      setServerError("Pick a test first.");
      return;
    }
    const payload = {
      test_type_id: Number(values.test_type_id),
      value: isQualitative || !values.value ? null : Number(values.value),
      value_qualitative: isQualitative ? values.value_qualitative.trim() : "",
      unit: values.unit || selectedTest.default_unit,
      measured_at: values.measured_at || null,
    };
    try {
      if (editingResult) {
        await update.mutateAsync({ id: editingResult.id, ...payload });
      } else {
        await create.mutateAsync(payload);
      }
      reset();
      onOpenChange(false);
    } catch (err: unknown) {
      const e = err as { response?: { data?: Record<string, string[] | string> } };
      const data = e.response?.data;
      if (data?.value) {
        const v = data.value;
        setServerError(`Value: ${Array.isArray(v) ? v[0] : v}`);
      } else if (data?.unit) {
        const u = data.unit;
        setServerError(`Unit: ${Array.isArray(u) ? u[0] : u}`);
      } else if (data?.test_type_id) {
        setServerError("Unknown test type. Refresh and try again.");
      } else {
        setServerError(isEditing ? "Couldn't update. Try again." : "Couldn't save. Try again.");
      }
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{isEditing ? "Edit lab result" : "Add a lab result"}</DialogTitle>
          <DialogDescription>
            {isEditing
              ? "Adjust the value, unit, or date. The test itself can't be changed — create a new result if you need a different test."
              : "Type in one value from a report."}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
          {/* Test selector — grouped.
              Locked both in edit mode (backend rejects test_type changes) and
              when opened from a test-specific detail page via defaultTestAbbrev.
              When locked we render the test name as a read-only label instead
              of a disabled Select, because:
                (a) a disabled dropdown still invites the user to click it, and
                (b) auto-created tests (no category) aren't in categoriesWithTests,
                    so a locked Select would fall back to "Choose a test…". */}
          <div className="space-y-2">
            <Label htmlFor="test_type_id">Test</Label>
            {testSelectorLocked ? (
              <div
                id="test_type_id"
                className="flex h-11 items-center rounded-md border border-input bg-muted px-3 text-sm text-foreground"
                aria-readonly="true"
              >
                <span className="truncate">
                  {selectedTest?.name ??
                    editingResult?.test.name ??
                    defaultTestAbbrev ??
                    "—"}
                </span>
                {(selectedTest?.default_unit ?? editingResult?.test.default_unit) && (
                  <span className="ml-2 shrink-0 text-xs text-muted-foreground">
                    ({selectedTest?.default_unit ?? editingResult?.test.default_unit})
                  </span>
                )}
              </div>
            ) : (
              <Select
                value={selectedTestId || undefined}
                onValueChange={(v) => setValue("test_type_id", v, { shouldValidate: true })}
              >
                <SelectTrigger id="test_type_id">
                  <SelectValue placeholder="Choose a test…" />
                </SelectTrigger>
                <SelectContent className="max-h-80">
                  {categoriesWithTests.map((group) => (
                    <TestGroup key={group.key} category={group} tests={group.tests} />
                  ))}
                </SelectContent>
              </Select>
            )}
            <input
              type="hidden"
              {...register("test_type_id", { required: "Pick a test" })}
            />
            {errors.test_type_id && (
              <p className="text-xs text-error-700">{errors.test_type_id.message}</p>
            )}
          </div>

          {/* Value + unit OR qualitative */}
          {isQualitative ? (
            <div className="space-y-2">
              <Label htmlFor="value_qualitative">Result</Label>
              {/* Controlled Select: reads value_qualitative from form state so
                  edit mode shows the stored result (non-reactive / reactive /
                  indeterminate) pre-selected. Passes `undefined` when empty
                  so Radix renders the placeholder. */}
              <Select
                value={watch("value_qualitative") || undefined}
                onValueChange={(v) => setValue("value_qualitative", v, { shouldValidate: true })}
              >
                <SelectTrigger id="value_qualitative">
                  <SelectValue placeholder="Choose…" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="non-reactive">Non-reactive (negative)</SelectItem>
                  <SelectItem value="reactive">Reactive (positive)</SelectItem>
                  <SelectItem value="indeterminate">Indeterminate</SelectItem>
                </SelectContent>
              </Select>
              <input type="hidden" {...register("value_qualitative")} />
            </div>
          ) : (
            <NumericValueUnitField
              test={selectedTest}
              register={register}
              selectedUnit={watch("unit") || undefined}
              onUnitChange={(u) => setValue("unit", u, { shouldValidate: false })}
            />
          )}

          {/* Date */}
          <div className="space-y-2">
            <Label htmlFor="measured_at">Date measured</Label>
            <Input
              id="measured_at"
              type="date"
              {...register("measured_at")}
            />
          </div>

          {serverError && (
            <div role="alert" className="rounded-md bg-error-50 p-3 text-sm text-error-700">
              {serverError}
            </div>
          )}

          <DialogFooter>
            <Button type="button" variant="ghost" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting || !selectedTest}>
              {isSubmitting
                ? isEditing
                  ? "Updating…"
                  : "Saving…"
                : isEditing
                  ? "Update result"
                  : "Save result"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

/**
 * Numeric value + unit pair. The unit field is a Select populated from
 * [default_unit, ...alternative_units] when the test has alternatives,
 * or a read-only label when it doesn't.
 */
function NumericValueUnitField({
  test,
  register,
  selectedUnit,
  onUnitChange,
}: {
  test: LabTestEntry | undefined;
  register: UseFormRegister<FormValues>;
  selectedUnit: string | undefined;
  onUnitChange: (unit: string) => void;
}) {
  const unitOptions = useMemo(() => {
    if (!test) return [] as string[];
    // De-dupe defensively in case a catalog row ever lists default_unit in alternatives
    const all = [test.default_unit, ...test.alternative_units];
    return Array.from(new Set(all.filter(Boolean)));
  }, [test]);

  const hasAlternatives = unitOptions.length > 1;

  // Placeholder reflects the currently-selected unit so the user sees the
  // expected magnitude. Source: backend catalog (LabTestEntry.sample_values),
  // keyed by unit string. E.g. hgb in g/dL → "14.0", hgb in g/L → "140".
  const activeUnit = selectedUnit ?? test?.default_unit ?? "";
  const placeholder = test?.sample_values?.[activeUnit] ?? GENERIC_PLACEHOLDER;

  return (
    <div className="grid grid-cols-[1fr_auto] gap-2">
      <div className="space-y-2">
        <Label htmlFor="value">Value</Label>
        <Input
          id="value"
          type="number"
          step="any"
          placeholder={placeholder}
          {...register("value", test ? { required: "Required" } : {})}
          disabled={!test}
        />
      </div>
      <div className="space-y-2">
        <Label htmlFor="unit">Unit</Label>
        {!test ? (
          <Input id="unit" className="w-32" disabled />
        ) : hasAlternatives ? (
          <Select value={selectedUnit ?? test.default_unit} onValueChange={onUnitChange}>
            <SelectTrigger id="unit" className="w-32">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {unitOptions.map((u) => (
                <SelectItem key={u} value={u}>
                  {u}
                  {u === test.default_unit && (
                    <span className="ml-2 text-[10px] text-muted-foreground">default</span>
                  )}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        ) : (
          <div
            id="unit"
            className="flex h-11 w-32 items-center rounded-md border border-input bg-muted px-3 font-mono text-sm text-muted-foreground"
            aria-label={`Unit: ${test.default_unit}`}
          >
            {test.default_unit || "—"}
          </div>
        )}
      </div>
      {test && hasAlternatives && (
        <div className="col-span-2 -mt-1 text-xs text-muted-foreground">
          <p>
            Stored as <span className="font-mono">{test.default_unit}</span>. Other units are
            converted automatically.
          </p>
        </div>
      )}
    </div>
  );
}

function TestGroup({ category, tests }: { category: { key: string; name: string }; tests: LabTestEntry[] }) {
  return (
    <>
      <div className="px-2 py-1.5 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
        {category.name}
      </div>
      {tests.map((t) => (
        <SelectItem key={t.id} value={String(t.id)}>
          {t.name}
          {t.default_unit && (
            <span className="ml-2 text-xs text-muted-foreground">({t.default_unit})</span>
          )}
        </SelectItem>
      ))}
    </>
  );
}
