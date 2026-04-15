/**
 * Onboarding Conditions — /onboarding/conditions
 * Per docs/patient-app-requirements.md §2.2 and design.md §5.3.
 *
 *  - ThreeModeInput at top
 *  - Common condition chips
 *  - Cancer diagnosis selector with rose accent (cancer fields only)
 */
import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { OnboardingStepShell } from "@/components/healthkey/OnboardingStepShell";
import { ThreeModeInput } from "@/components/healthkey/ThreeModeInput";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useFormSettings, usePatientInfo, useUpdatePatientInfo } from "@/features/patient-profile/api";

export function Conditions() {
  const navigate = useNavigate();
  const { data: patient } = usePatientInfo();
  const { data: formSettings } = useFormSettings();
  const update = useUpdatePatientInfo();
  const [mode, setMode] = useState<"manual" | "upload" | "ehr">("manual");

  const selectedConditions: string[] = (patient?.details?.conditions as string[]) ?? [];

  const toggleCondition = (value: string) => {
    const next = selectedConditions.includes(value)
      ? selectedConditions.filter((c) => c !== value)
      : [...selectedConditions, value];
    update.mutate({ details: { conditions: next } });
  };

  const setDisease = (value: string) => {
    update.mutate({ disease: value });
  };

  return (
    <OnboardingStepShell
      step={3}
      totalSteps={8}
      title="Conditions and diagnoses"
      description="Add anything you know. We'll fill in the rest from your records."
      backTo="/onboarding/demographics"
      skipTo="/onboarding/lifestyle"
      onContinue={() => navigate("/onboarding/lifestyle")}
      isSaving={update.isPending}
    >
      <ThreeModeInput active={mode} onChange={setMode} />

      <section className="mb-8">
        <h3 className="mb-3 text-h4 text-foreground">Common conditions</h3>
        <div className="flex flex-wrap gap-2">
          {formSettings?.common_conditions.map((opt) => {
            const active = selectedConditions.includes(String(opt.value));
            return (
              <button
                key={opt.value}
                type="button"
                onClick={() => toggleCondition(String(opt.value))}
                aria-pressed={active}
                className={[
                  "rounded-full border px-4 py-2 text-body font-medium transition-colors",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-700 focus-visible:ring-offset-2",
                  active
                    ? "border-brand-700 bg-brand-700 text-white"
                    : "border-border bg-background text-foreground hover:bg-muted",
                ].join(" ")}
              >
                {opt.label}
              </button>
            );
          })}
        </div>
      </section>

      <section className="rounded-md border border-error-200 bg-error-50 p-4">
        <div className="mb-2 flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-error-700" aria-hidden="true" />
          <h3 className="text-h4 text-foreground">Cancer diagnosis (optional)</h3>
        </div>
        <p className="mb-3 text-body text-muted-foreground">
          If you have a cancer diagnosis, picking it here will unlock relevant fields and trial matching later.
        </p>
        <Select
          // Radix forbids "" as item value. Empty string in our data model means
          // "no cancer diagnosis"; map to/from a sentinel "_none_" at the boundary.
          value={patient?.disease ? patient.disease : "_none_"}
          onValueChange={(v) => setDisease(v === "_none_" ? "" : v)}
        >
          <SelectTrigger aria-label="Cancer diagnosis">
            <SelectValue placeholder="Choose…" />
          </SelectTrigger>
          <SelectContent>
            {formSettings?.diseases.map((opt) => (
              <SelectItem key={String(opt.value) || "_none_"} value={String(opt.value) || "_none_"}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </section>
    </OnboardingStepShell>
  );
}
