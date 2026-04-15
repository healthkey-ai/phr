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
import { useCatalog, useCreateLabResult } from "@/features/labs/api";
import type { LabCategory, LabTestType } from "@/types/labs";

/** Fallback placeholder when the backend catalog doesn't supply one. */
const GENERIC_PLACEHOLDER = "e.g. 12.5";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Pre-select a test by abbreviation (e.g. opening from a specific card) */
  defaultTestAbbrev?: string;
}

interface FormValues {
  test_type_id: string; // Select gives us strings
  value: string;
  value_qualitative: string;
  unit: string;
  measured_at: string;
}

export function LabManualEntryDialog({ open, onOpenChange, defaultTestAbbrev }: Props) {
  const { data: catalog } = useCatalog();
  const create = useCreateLabResult();
  const [serverError, setServerError] = useState<string | null>(null);

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

  // Group tests by category for a sensible Select
  const categoriesWithTests = useMemo(() => {
    if (!catalog) return [];
    return catalog.categories
      .map((cat) => ({
        category: cat,
        tests: catalog.tests.filter((t) => t.category === cat.key),
      }))
      .filter((c) => c.tests.length > 0);
  }, [catalog]);

  const selectedTestId = watch("test_type_id");
  const selectedTest: LabTestType | undefined = useMemo(() => {
    if (!catalog || !selectedTestId) return undefined;
    return catalog.tests.find((t) => String(t.id) === selectedTestId);
  }, [catalog, selectedTestId]);

  // Pre-select a test when defaultTestAbbrev is passed
  useEffect(() => {
    if (defaultTestAbbrev && catalog && !selectedTestId) {
      const t = catalog.tests.find((t) => t.abbreviation === defaultTestAbbrev);
      if (t) setValue("test_type_id", String(t.id));
    }
  }, [defaultTestAbbrev, catalog, selectedTestId, setValue]);

  // When test changes, default the unit to that test's default_unit
  useEffect(() => {
    if (selectedTest) {
      setValue("unit", selectedTest.default_unit, { shouldValidate: false });
    }
  }, [selectedTest?.id, setValue]); // eslint-disable-line react-hooks/exhaustive-deps

  const isQualitative = selectedTest?.value_type === "qualitative";

  const onSubmit = async (values: FormValues) => {
    setServerError(null);
    if (!selectedTest) {
      setServerError("Pick a test first.");
      return;
    }
    try {
      await create.mutateAsync({
        test_type_id: Number(values.test_type_id),
        value: isQualitative || !values.value ? null : Number(values.value),
        value_qualitative: isQualitative ? values.value_qualitative.trim() : "",
        unit: values.unit || selectedTest.default_unit,
        measured_at: values.measured_at || null,
      });
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
        setServerError("Couldn't save. Try again.");
      }
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Add a lab result</DialogTitle>
          <DialogDescription>
            Type in one value from a report. Upload + automatic reading is coming in Phase 2.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
          {/* Test selector — grouped */}
          <div className="space-y-2">
            <Label htmlFor="test_type_id">Test</Label>
            <Select
              value={selectedTestId || undefined}
              onValueChange={(v) => setValue("test_type_id", v, { shouldValidate: true })}
            >
              <SelectTrigger id="test_type_id">
                <SelectValue placeholder="Choose a test…" />
              </SelectTrigger>
              <SelectContent className="max-h-80">
                {categoriesWithTests.map((group) => (
                  <TestGroup key={group.category.key} category={group.category} tests={group.tests} />
                ))}
              </SelectContent>
            </Select>
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
              <Select
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
              {isSubmitting ? "Saving…" : "Save result"}
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
  test: LabTestType | undefined;
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
  // expected magnitude. Source: backend catalog (LabTestType.sample_values),
  // keyed by unit string. E.g. hgb in g/dL → "14.0", hgb in g/L → "140".
  const activeUnit = selectedUnit ?? test?.default_unit ?? "";
  const placeholder = test?.sample_values?.[activeUnit] ?? GENERIC_PLACEHOLDER;

  // Normal range for the active unit, pre-converted by the backend so the UI
  // doesn't carry unit-conversion math. Empty for qualitative tests or tests
  // where the converter couldn't translate the default-unit range.
  const range = test?.reference_ranges_by_unit?.[activeUnit];

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
      {test && (
        <div className="col-span-2 -mt-1 space-y-0.5 text-xs text-muted-foreground">
          {range && (
            <p>
              Normal range:{" "}
              <span className="font-mono text-foreground">
                {formatRange(range[0], range[1])} {activeUnit}
              </span>
            </p>
          )}
          {hasAlternatives && (
            <p>
              Stored as <span className="font-mono">{test.default_unit}</span>. Other units are
              converted automatically.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

/** Render a numeric range compactly — "12.0–17.5". Drops trailing ".0"
 * only when both bounds are integers so "150–400" looks clean but
 * "12.0–17.5" stays readable. */
function formatRange(lo: number, hi: number): string {
  const bothInt = Number.isInteger(lo) && Number.isInteger(hi);
  const format = (n: number) => (bothInt ? String(n) : String(Number(n.toFixed(3))));
  return `${format(lo)}–${format(hi)}`;
}

function TestGroup({ category, tests }: { category: LabCategory; tests: LabTestType[] }) {
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
