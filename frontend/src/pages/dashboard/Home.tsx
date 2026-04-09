/**
 * Dashboard Home tab — /dashboard
 * Per docs/patient-app-design.md §5.6.
 *
 * Hierarchy: greeting + completeness → quick actions → recent activity → record sections.
 * Optimised for the 23-second daily glance, NOT engagement metrics.
 */
import { Download, FileText, Link2, Plus, Target } from "lucide-react";

import { CompletenessIndicator } from "@/components/healthkey/CompletenessIndicator";
import { DataSourceBadge } from "@/components/healthkey/DataSourceBadge";
import { Card, CardContent } from "@/components/ui/card";
import { usePatientInfo, useProfileCompleteness } from "@/features/patient-profile/api";

function timeOfDayGreeting() {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 18) return "Good afternoon";
  return "Good evening";
}

const QUICK_ACTIONS = [
  { icon: Link2, label: "Share", disabled: true, hint: "Phase 3" },
  { icon: Plus, label: "Add data", disabled: false },
  { icon: Target, label: "Trials", disabled: true, hint: "Phase 3" },
  { icon: Download, label: "Export", disabled: true, hint: "Phase 4" },
];

export function Home() {
  const { data: patient } = usePatientInfo();
  const { data: completeness } = useProfileCompleteness();

  const greetingName = patient?.first_name || "there";

  return (
    <div className="mx-auto max-w-4xl p-4 sm:p-6 lg:p-10">
      {/* Greeting + completeness */}
      <header className="mb-8 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-h1 text-foreground">
            {timeOfDayGreeting()}, {greetingName}
          </h1>
          <p className="mt-1 text-body-lg text-muted-foreground">
            Your record is up to date.
          </p>
        </div>
        <CompletenessIndicator value={completeness?.completeness_score ?? 0} size={72} />
      </header>

      {/* Quick actions */}
      <section className="mb-10">
        <h2 className="sr-only">Quick actions</h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {QUICK_ACTIONS.map(({ icon: Icon, label, disabled, hint }) => (
            <button
              key={label}
              disabled={disabled}
              className={[
                "flex flex-col items-center justify-center gap-2 rounded-md border border-border bg-card p-4 text-center transition-colors",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-700 focus-visible:ring-offset-2",
                disabled ? "cursor-not-allowed opacity-50" : "hover:bg-muted",
              ].join(" ")}
            >
              <Icon className="h-6 w-6 text-brand-700" />
              <span className="text-body font-semibold">{label}</span>
              {hint && <span className="text-caption text-muted-foreground">{hint}</span>}
            </button>
          ))}
        </div>
      </section>

      {/* Recent activity */}
      <section className="mb-10">
        <h2 className="mb-3 text-h3 text-foreground">Recent activity</h2>
        <Card>
          <CardContent className="p-6">
            <ul className="space-y-3 text-body">
              <li className="flex items-center gap-3">
                <span className="h-2 w-2 rounded-full bg-brand-700" />
                <span className="flex-1 text-foreground">Profile created</span>
                <span className="text-caption text-muted-foreground">just now</span>
              </li>
            </ul>
          </CardContent>
        </Card>
      </section>

      {/* Sections */}
      <section>
        <h2 className="mb-3 text-h3 text-foreground">Sections</h2>
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <Card>
            <CardContent className="p-6">
              <div className="mb-3 flex items-center justify-between">
                <h3 className="text-h4 text-foreground">Identity</h3>
                <FileText className="h-4 w-4 text-muted-foreground" />
              </div>
              {patient?.first_name ? (
                <>
                  <p className="text-body font-medium text-foreground">
                    {patient.first_name} {patient.last_name}
                  </p>
                  <p className="text-body text-muted-foreground">
                    {patient.dob && `Born ${new Date(patient.dob).getFullYear()}`}
                    {patient.gender && ` · ${patient.gender}`}
                  </p>
                  <div className="mt-3">
                    <DataSourceBadge source="manual" detail="You" />
                  </div>
                </>
              ) : (
                <p className="text-body text-muted-foreground">
                  Add your basics in onboarding to see them here.
                </p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-6">
              <h3 className="mb-3 text-h4 text-foreground">Conditions</h3>
              {(patient?.details?.conditions as string[])?.length ? (
                <ul className="space-y-1 text-body">
                  {(patient!.details.conditions as string[]).map((c) => (
                    <li key={c} className="text-foreground">• {c}</li>
                  ))}
                </ul>
              ) : (
                <p className="text-body text-muted-foreground">
                  No conditions added yet.
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      </section>
    </div>
  );
}
