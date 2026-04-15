/**
 * Dashboard Records tab — /dashboard/records
 * Per docs/patient-app-design.md §5.7.
 *
 * Phase 1: shows the structured record. Lab trends + timeline + conflicts come in Phase 2.
 */
import { useState } from "react";
import { Plus } from "lucide-react";

import { DataSourceBadge } from "@/components/healthkey/DataSourceBadge";
import { LabManualEntryDialog } from "@/components/labs/LabManualEntryDialog";
import { LabValueCard } from "@/components/labs/LabValueCard";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useCatalog, useLabResults } from "@/features/labs/api";
import { usePatientInfo } from "@/features/patient-profile/api";

export function Records() {
  const { data: patient, isLoading } = usePatientInfo();

  if (isLoading) {
    return <div className="p-6 text-body text-muted-foreground">Loading…</div>;
  }

  return (
    <div className="mx-auto max-w-4xl p-4 sm:p-6 lg:p-10">
      <h1 className="mb-6 text-h1 text-foreground">Your records</h1>

      {/* Identity */}
      <section className="mb-6">
        <h2 className="mb-3 text-h3 text-foreground">Identity</h2>
        <Card>
          <CardContent className="p-6">
            {patient?.first_name ? (
              <>
                <p className="text-h4 text-foreground">
                  {patient.first_name} {patient.last_name}
                </p>
                <p className="mt-1 text-body text-muted-foreground">
                  {patient.dob && `Born ${new Date(patient.dob).getFullYear()}`}
                  {patient.gender && ` · ${patient.gender}`}
                  {patient.height_cm && ` · ${patient.height_cm} cm`}
                  {patient.weight_kg && ` · ${patient.weight_kg} kg`}
                  {patient.bmi && ` · BMI ${patient.bmi}`}
                </p>
                <div className="mt-3">
                  <DataSourceBadge source="manual" detail="You" />
                </div>
              </>
            ) : (
              <EmptyState
                title="Add your basics"
                body="Tell us your name, date of birth, and a few other essentials in onboarding."
                cta={{ to: "/onboarding/demographics", label: "Start onboarding" }}
              />
            )}
          </CardContent>
        </Card>
      </section>

      {/* Conditions */}
      <section className="mb-6">
        <h2 className="mb-3 text-h3 text-foreground">Conditions</h2>
        <Card>
          <CardContent className="p-6">
            {(patient?.details?.conditions as string[] | undefined)?.length ? (
              <>
                <ul className="space-y-2 text-body text-foreground">
                  {(patient!.details.conditions as string[]).map((c) => (
                    <li key={c}>• {c}</li>
                  ))}
                </ul>
                {patient?.disease && (
                  <p className="mt-3 text-body">
                    <span className="text-muted-foreground">Cancer: </span>
                    <span className="font-semibold text-foreground">{patient.disease}</span>
                  </p>
                )}
                <div className="mt-3">
                  <DataSourceBadge source="manual" detail="You" />
                </div>
              </>
            ) : (
              <EmptyState
                title="No conditions added"
                body="We'll show your active diagnoses and any provider notes here once added."
                cta={{ to: "/onboarding/conditions", label: "Add conditions" }}
              />
            )}
          </CardContent>
        </Card>
      </section>

      {/* Lifestyle */}
      <section className="mb-6">
        <h2 className="mb-3 text-h3 text-foreground">Lifestyle</h2>
        <Card>
          <CardContent className="p-6">
            {patient?.details &&
            Object.keys(patient.details).some((k) =>
              ["smokingStatus", "alcoholFrequency", "exerciseLevel", "dietType"].includes(k),
            ) ? (
              <dl className="space-y-2 text-body">
                {patient.details.smokingStatus !== undefined && (
                  <Row label="Smoking" value={String(patient.details.smokingStatus)} />
                )}
                {patient.details.alcoholFrequency !== undefined && (
                  <Row label="Alcohol" value={String(patient.details.alcoholFrequency)} />
                )}
                {patient.details.exerciseLevel !== undefined && (
                  <Row label="Exercise" value={String(patient.details.exerciseLevel)} />
                )}
                {patient.details.dietType !== undefined && (
                  <Row label="Diet" value={String(patient.details.dietType)} />
                )}
              </dl>
            ) : (
              <EmptyState
                title="No lifestyle info added"
                body="Smoking, alcohol, exercise, and diet help match you to relevant trials."
                cta={{ to: "/onboarding/lifestyle", label: "Add lifestyle info" }}
              />
            )}
          </CardContent>
        </Card>
      </section>

      {/* Lab values */}
      <LabsSection />

      {/* Connected sources placeholder */}
      <section>
        <h2 className="mb-3 text-h3 text-foreground">Connected sources</h2>
        <Card>
          <CardContent className="p-6">
            <EmptyState
              title="No connected providers yet"
              body="Connect Epic, Cerner, athenahealth and more to pull your records automatically. Coming in Phase 2."
            />
          </CardContent>
        </Card>
      </section>
    </div>
  );
}

/**
 * Labs section — lists unique test cards for whatever the patient has entered.
 * Empty state points at the manual entry dialog.
 */
function LabsSection() {
  const [dialogOpen, setDialogOpen] = useState(false);
  const { data: results = [], isLoading } = useLabResults();
  const { data: catalog } = useCatalog();

  // Unique test abbreviations across all results, preserving recency order
  const testAbbrevs = Array.from(new Set(results.map((r) => r.test.abbreviation)));

  return (
    <section className="mb-6">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-h3 text-foreground">Lab values</h2>
        <Button
          size="sm"
          variant="secondary"
          onClick={() => setDialogOpen(true)}
          disabled={!catalog}
        >
          <Plus className="mr-1 h-4 w-4" /> Add lab result
        </Button>
      </div>

      {isLoading ? (
        <Card>
          <CardContent className="p-6">
            <div className="h-4 w-32 animate-pulse rounded bg-muted" />
          </CardContent>
        </Card>
      ) : testAbbrevs.length === 0 ? (
        <Card>
          <CardContent className="p-6">
            <EmptyState
              title="No lab values yet"
              body="Add your first result to see it trend over time. Upload + automatic reading of lab reports is coming in Phase 2."
            />
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {testAbbrevs.map((abbrev) => (
            <LabValueCard key={abbrev} testAbbrev={abbrev} />
          ))}
        </div>
      )}

      <LabManualEntryDialog open={dialogOpen} onOpenChange={setDialogOpen} />
    </section>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="font-medium text-foreground">{value}</dd>
    </div>
  );
}

function EmptyState({
  title,
  body,
  cta,
}: {
  title: string;
  body: string;
  cta?: { to: string; label: string };
}) {
  return (
    <div className="py-4 text-center">
      <p className="text-h4 text-foreground">{title}</p>
      <p className="mt-1 text-body text-muted-foreground">{body}</p>
      {cta && (
        <a
          href={cta.to}
          className="mt-3 inline-block text-body font-semibold text-brand-700 hover:underline"
        >
          {cta.label} →
        </a>
      )}
    </div>
  );
}
