/**
 * Onboarding Family History — /onboarding/family
 * Per docs/patient-app-requirements.md §2.4.
 *
 * Conditions × Relatives matrix. Implemented as a CSS grid with explicit
 * track sizing so:
 *  - Data columns are perfectly even (1fr each)
 *  - Headers don't wrap mid-word (whitespace-normal + leading-tight)
 *  - Sticky first column for the condition labels
 *  - Horizontal scroll on very narrow screens (min-w fallback)
 */
import { useNavigate } from "react-router-dom";

import { OnboardingStepShell } from "@/components/healthkey/OnboardingStepShell";
import { Checkbox } from "@/components/ui/checkbox";
import { useFormSettings, usePatientInfo, useUpdatePatientInfo } from "@/features/patient-profile/api";

type FamilyHistory = Record<string, Record<string, boolean>>;

export function Family() {
  const navigate = useNavigate();
  const { data: patient } = usePatientInfo();
  const { data: formSettings } = useFormSettings();
  const update = useUpdatePatientInfo();

  const familyHistory = (patient?.details?.familyHistory as FamilyHistory) ?? {};

  const toggle = (relativeKey: string, conditionKey: string) => {
    const relativeRecord = familyHistory[relativeKey] ?? {};
    const next: FamilyHistory = {
      ...familyHistory,
      [relativeKey]: { ...relativeRecord, [conditionKey]: !relativeRecord[conditionKey] },
    };
    update.mutate({ details: { familyHistory: next } });
  };

  const conditions = formSettings?.family_conditions ?? [];

  // Shorten "Maternal/Paternal grandparent" so it wraps cleanly into a 50px
  // column ("Maternal" / "GP"). Full label is announced via aria-label on the
  // checkboxes below, so screen-reader users still get the unabbreviated form.
  const relatives = (formSettings?.family_relatives ?? []).map((r) => ({
    ...r,
    shortLabel: String(r.label).replace("grandparent", "GP"),
  }));

  // Grid track sizing — picked to fit a 375px viewport (iPhone SE/13 mini):
  //   343px available  =  86px label col  +  5 × 50px data cols  +  spare
  // On wider screens, 1fr units expand the columns to fill the container.
  const gridTemplate = `minmax(86px, 1.4fr) repeat(${relatives.length}, minmax(50px, 1fr))`;
  const minWidth = 86 + relatives.length * 50;

  return (
    <OnboardingStepShell
      step={5}
      totalSteps={8}
      title="Family history"
      description="Tap any condition that runs in your family. We use this to flag inherited risk."
      backTo="/onboarding/lifestyle"
      skipTo="/onboarding/summary"
      onContinue={() => navigate("/onboarding/summary")}
      isSaving={update.isPending}
    >
      <div
        className="overflow-x-auto rounded-md border border-border bg-card"
        role="region"
        aria-label="Family history matrix"
      >
        <div role="grid" style={{ minWidth }} className="text-sm">
          {/* Header row */}
          <div
            role="row"
            className="grid border-b border-border bg-muted/50"
            style={{ gridTemplateColumns: gridTemplate }}
          >
            <div
              role="columnheader"
              className="px-2 py-2 text-left text-[11px] font-semibold uppercase tracking-wide text-muted-foreground"
            >
              Condition
            </div>
            {relatives.map((rel) => (
              <div
                key={rel.value}
                role="columnheader"
                className="px-0.5 py-2 text-center text-[11px] font-semibold leading-tight text-foreground"
                title={rel.label}
              >
                {rel.shortLabel}
              </div>
            ))}
          </div>

          {/* Body rows */}
          {conditions.map((cond, idx) => (
            <div
              key={cond.value}
              role="row"
              className={[
                "grid items-center transition-colors hover:bg-muted/40",
                idx > 0 && "border-t border-border",
              ]
                .filter(Boolean)
                .join(" ")}
              style={{ gridTemplateColumns: gridTemplate }}
            >
              <div
                role="rowheader"
                className="px-2 py-3 text-left text-[13px] font-medium leading-tight text-foreground"
              >
                {cond.label}
              </div>
              {relatives.map((rel) => {
                const relKey = String(rel.value);
                const condKey = String(cond.value);
                const checked = Boolean((familyHistory[relKey] ?? {})[condKey]);
                return (
                  <div
                    key={rel.value}
                    role="gridcell"
                    className="flex items-center justify-center px-0.5 py-3"
                  >
                    <Checkbox
                      checked={checked}
                      onCheckedChange={() => toggle(relKey, condKey)}
                      aria-label={`${cond.label} in ${rel.label}`}
                    />
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      </div>

      <p className="mt-3 text-caption text-muted-foreground">
        * GP — grandparent
      </p>
    </OnboardingStepShell>
  );
}
