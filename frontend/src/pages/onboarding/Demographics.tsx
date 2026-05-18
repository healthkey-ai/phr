/**
 * Onboarding Demographics — /onboarding/demographics
 * Per docs/patient-app-requirements.md §2.1 and design.md §5.3.
 *
 * Auto-save on blur. No explicit Save button. Skip is always available.
 */
import { useState } from "react";
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
import { usePatientInfo, useUpdatePatientInfo, useFormSettings } from "@/features/patient-profile/api";

export function Demographics() {
  const navigate = useNavigate();
  const { data: patient } = usePatientInfo();
  const { data: formSettings } = useFormSettings();
  const update = useUpdatePatientInfo();

  interface FormValues {
    first_name: string;
    last_name: string;
    dob: string;
    gender: string;
    height_cm: string | number;
    weight_kg: string | number;
    country: string;
    postal_code: string;
  }

  const [overrides, setOverrides] = useState<Partial<FormValues>>({});

  const values: FormValues = {
    first_name: overrides.first_name ?? patient?.first_name ?? "",
    last_name: overrides.last_name ?? patient?.last_name ?? "",
    dob: overrides.dob ?? patient?.dob ?? "",
    gender: overrides.gender ?? patient?.gender ?? "",
    height_cm: overrides.height_cm ?? patient?.height_cm ?? "",
    weight_kg: overrides.weight_kg ?? patient?.weight_kg ?? "",
    country: overrides.country ?? patient?.country ?? "",
    postal_code: overrides.postal_code ?? patient?.postal_code ?? "",
  };

  const handleBlur = (field: keyof typeof values) => {
    const value = values[field];
    const current = patient?.[field] ?? "";
    if (value === current) return;

    const payload: Record<string, unknown> = {};
    if (field === "height_cm" || field === "weight_kg") {
      payload[field] = value === "" ? null : Number(value);
    } else {
      payload[field] = value || "";
    }
    update.mutate(payload);
  };

  return (
    <OnboardingStepShell
      step={2}
      totalSteps={8}
      title="The basics"
      description="Just the essentials. We'll fill in more from your records."
      backTo="/onboarding"
      skipTo="/onboarding/conditions"
      onContinue={() => navigate("/onboarding/conditions")}
      isSaving={update.isPending}
    >
      <div className="space-y-5">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="first_name">First name</Label>
            <Input
              id="first_name"
              value={values.first_name}
              onChange={(e) => setOverrides((prev) => ({ ...prev, first_name: e.target.value }))}
              onBlur={() => handleBlur("first_name")}
              autoComplete="given-name"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="last_name">Last name</Label>
            <Input
              id="last_name"
              value={values.last_name}
              onChange={(e) => setOverrides((prev) => ({ ...prev, last_name: e.target.value }))}
              onBlur={() => handleBlur("last_name")}
              autoComplete="family-name"
            />
          </div>
        </div>

        <div className="space-y-2">
          <Label htmlFor="dob">Date of birth</Label>
          <Input
            id="dob"
            type="date"
            value={values.dob}
            onChange={(e) => setOverrides((prev) => ({ ...prev, dob: e.target.value }))}
            onBlur={() => handleBlur("dob")}
            autoComplete="bday"
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="gender">Gender</Label>
          <Select
            // Radix Select forbids "" as a value, so we map empty → undefined.
            value={values.gender || undefined}
            onValueChange={(v) => {
              setOverrides((prev) => ({ ...prev, gender: v }));
              update.mutate({ gender: v });
            }}
          >
            <SelectTrigger id="gender">
              <SelectValue placeholder="Choose…" />
            </SelectTrigger>
            <SelectContent>
              {formSettings?.gender.map((opt) => (
                <SelectItem key={String(opt.value)} value={String(opt.value)}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="height_cm">Height (cm)</Label>
            <Input
              id="height_cm"
              type="number"
              min="50"
              max="300"
              value={values.height_cm}
              onChange={(e) => setOverrides((prev) => ({ ...prev, height_cm: e.target.value }))}
              onBlur={() => handleBlur("height_cm")}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="weight_kg">Weight (kg)</Label>
            <Input
              id="weight_kg"
              type="number"
              min="20"
              max="500"
              step="0.1"
              value={values.weight_kg}
              onChange={(e) => setOverrides((prev) => ({ ...prev, weight_kg: e.target.value }))}
              onBlur={() => handleBlur("weight_kg")}
            />
          </div>
        </div>

        {patient?.bmi != null && (
          <p className="text-body text-muted-foreground">
            BMI: <span className="font-semibold text-foreground">{patient.bmi}</span>
          </p>
        )}

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="country">Country (3-letter)</Label>
            <Input
              id="country"
              maxLength={3}
              placeholder="USA"
              value={values.country}
              onChange={(e) => setOverrides((prev) => ({ ...prev, country: e.target.value.toUpperCase() }))}
              onBlur={() => handleBlur("country")}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="postal_code">Postal code</Label>
            <Input
              id="postal_code"
              value={values.postal_code}
              onChange={(e) => setOverrides((prev) => ({ ...prev, postal_code: e.target.value }))}
              onBlur={() => handleBlur("postal_code")}
              autoComplete="postal-code"
            />
          </div>
        </div>
      </div>
    </OnboardingStepShell>
  );
}
