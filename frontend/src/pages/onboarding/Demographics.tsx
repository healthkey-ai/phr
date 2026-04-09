/**
 * Onboarding Demographics — /onboarding/demographics
 * Per docs/patient-app-requirements.md §2.1 and design.md §5.3.
 *
 * Auto-save on blur. No explicit Save button. Skip is always available.
 */
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { OnboardingStepShell } from "@/components/healthkey/OnboardingStepShell";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { usePatientInfo, useUpdatePatientInfo, useFormSettings } from "@/features/patient-profile/api";

export function Demographics() {
  const navigate = useNavigate();
  const { data: patient } = usePatientInfo();
  const { data: formSettings } = useFormSettings();
  const update = useUpdatePatientInfo();

  // Local form state, hydrated from server, written through on blur
  const [values, setValues] = useState({
    first_name: "",
    last_name: "",
    dob: "",
    gender: "",
    height_cm: "" as string | number,
    weight_kg: "" as string | number,
    country: "",
    postal_code: "",
  });

  useEffect(() => {
    if (patient) {
      setValues({
        first_name: patient.first_name ?? "",
        last_name: patient.last_name ?? "",
        dob: patient.dob ?? "",
        gender: patient.gender ?? "",
        height_cm: patient.height_cm ?? "",
        weight_kg: patient.weight_kg ?? "",
        country: patient.country ?? "",
        postal_code: patient.postal_code ?? "",
      });
    }
  }, [patient]);

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
              onChange={(e) => setValues({ ...values, first_name: e.target.value })}
              onBlur={() => handleBlur("first_name")}
              autoComplete="given-name"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="last_name">Last name</Label>
            <Input
              id="last_name"
              value={values.last_name}
              onChange={(e) => setValues({ ...values, last_name: e.target.value })}
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
            onChange={(e) => setValues({ ...values, dob: e.target.value })}
            onBlur={() => handleBlur("dob")}
            autoComplete="bday"
          />
        </div>

        <div className="space-y-2">
          <Label htmlFor="gender">Gender</Label>
          <select
            id="gender"
            value={values.gender}
            onChange={(e) => {
              setValues({ ...values, gender: e.target.value });
              update.mutate({ gender: e.target.value });
            }}
            className="flex h-11 w-full rounded-md border border-input bg-background px-3 py-2 text-body-lg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-700 focus-visible:ring-offset-2"
          >
            <option value="">Choose…</option>
            {formSettings?.gender.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
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
              onChange={(e) => setValues({ ...values, height_cm: e.target.value })}
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
              onChange={(e) => setValues({ ...values, weight_kg: e.target.value })}
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
              onChange={(e) => setValues({ ...values, country: e.target.value.toUpperCase() })}
              onBlur={() => handleBlur("country")}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="postal_code">Postal code</Label>
            <Input
              id="postal_code"
              value={values.postal_code}
              onChange={(e) => setValues({ ...values, postal_code: e.target.value })}
              onBlur={() => handleBlur("postal_code")}
              autoComplete="postal-code"
            />
          </div>
        </div>
      </div>
    </OnboardingStepShell>
  );
}
