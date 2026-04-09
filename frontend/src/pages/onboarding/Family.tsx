/**
 * Onboarding Family History — /onboarding/family
 * Per docs/patient-app-requirements.md §2.4.
 *
 * Toggle grid: relatives × conditions. Stored as nested object in details.familyHistory.
 */
import { useNavigate } from "react-router-dom";

import { OnboardingStepShell } from "@/components/healthkey/OnboardingStepShell";
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

  return (
    <OnboardingStepShell
      step={5}
      totalSteps={8}
      title="Family history"
      description="Tap any condition that runs in your family."
      backTo="/onboarding/lifestyle"
      skipTo="/onboarding/summary"
      onContinue={() => navigate("/onboarding/summary")}
      isSaving={update.isPending}
    >
      <div className="overflow-x-auto">
        <table className="w-full border-collapse">
          <thead>
            <tr>
              <th className="sticky left-0 bg-background p-2 text-left text-body font-semibold text-foreground">
                <span className="sr-only">Condition</span>
              </th>
              {formSettings?.family_relatives.map((rel) => (
                <th
                  key={rel.value}
                  className="p-2 text-center text-caption font-semibold text-foreground"
                >
                  {rel.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {formSettings?.family_conditions.map((cond) => (
              <tr key={cond.value} className="border-t border-border">
                <th
                  scope="row"
                  className="sticky left-0 bg-background p-2 text-left text-body font-medium text-foreground"
                >
                  {cond.label}
                </th>
                {formSettings.family_relatives.map((rel) => {
                  const checked = Boolean(
                    (familyHistory[String(rel.value)] ?? {})[String(cond.value)],
                  );
                  return (
                    <td key={rel.value} className="p-2 text-center">
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => toggle(String(rel.value), String(cond.value))}
                        aria-label={`${cond.label} in ${rel.label}`}
                        className="h-5 w-5 cursor-pointer rounded border-input text-brand-700 focus:ring-brand-700"
                      />
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </OnboardingStepShell>
  );
}
