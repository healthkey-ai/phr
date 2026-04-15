/**
 * Onboarding Lifestyle — /onboarding/lifestyle
 * Per docs/patient-app-requirements.md §2.3.
 */
import { useNavigate } from "react-router-dom";

import { OnboardingStepShell } from "@/components/healthkey/OnboardingStepShell";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useFormSettings, usePatientInfo, useUpdatePatientInfo } from "@/features/patient-profile/api";

const LIFESTYLE_FIELDS = [
  { key: "smokingStatus", label: "Smoking", optionsKey: "smoking_status" as const },
  { key: "alcoholFrequency", label: "Alcohol", optionsKey: "alcohol_frequency" as const },
  { key: "exerciseLevel", label: "Exercise", optionsKey: "exercise_level" as const },
  { key: "dietType", label: "Diet", optionsKey: "diet_type" as const },
];

export function Lifestyle() {
  const navigate = useNavigate();
  const { data: patient } = usePatientInfo();
  const { data: formSettings } = useFormSettings();
  const update = useUpdatePatientInfo();

  const details = patient?.details ?? {};

  const setField = (key: string, value: string) => {
    update.mutate({ details: { [key]: value } });
  };

  return (
    <OnboardingStepShell
      step={4}
      totalSteps={8}
      title="Lifestyle"
      description="Things that affect your health day to day."
      backTo="/onboarding/conditions"
      skipTo="/onboarding/family"
      onContinue={() => navigate("/onboarding/family")}
      isSaving={update.isPending}
    >
      <div className="space-y-5">
        {LIFESTYLE_FIELDS.map((field) => {
          const current = (details[field.key] as string) || undefined;
          return (
            <div key={field.key} className="space-y-2">
              <Label htmlFor={field.key}>{field.label}</Label>
              <Select value={current} onValueChange={(v) => setField(field.key, v)}>
                <SelectTrigger id={field.key}>
                  <SelectValue placeholder="Choose…" />
                </SelectTrigger>
                <SelectContent>
                  {formSettings?.[field.optionsKey].map((opt) => (
                    <SelectItem key={String(opt.value)} value={String(opt.value)}>
                      {opt.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          );
        })}

        <div className="space-y-2">
          <Label htmlFor="occupation">Occupation</Label>
          <Input
            id="occupation"
            defaultValue={(details.occupation as string) ?? ""}
            onBlur={(e) => setField("occupation", e.target.value)}
          />
        </div>
      </div>
    </OnboardingStepShell>
  );
}
