/**
 * Onboarding Summary — /onboarding/summary
 * Per docs/patient-app-design.md §5.5.
 *
 * Animated completeness ring + per-category breakdown + recommended next.
 * No confetti. No celebration. Calm before clever.
 */
import { useNavigate } from "react-router-dom";
import { Link2 } from "lucide-react";

import { CompletenessIndicator } from "@/components/healthkey/CompletenessIndicator";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { useProfileCompleteness } from "@/features/patient-profile/api";

const CATEGORY_LABELS: Record<string, string> = {
  demographics: "Demographics",
  conditions: "Conditions",
  lifestyle: "Lifestyle",
  family: "Family history",
  labs: "Lab values",
  disease_profile: "Disease profile",
};

export function Summary() {
  const navigate = useNavigate();
  const { data, isLoading } = useProfileCompleteness();

  return (
    <div className="mx-auto flex min-h-screen max-w-xl flex-col px-4 py-6 sm:py-10">
      <div className="mb-12">
        <Progress value={100} aria-label="Onboarding complete" />
        <p className="mt-2 text-caption text-muted-foreground">Complete</p>
      </div>

      <main id="main" className="flex-1">
        <div className="flex flex-col items-center text-center">
          <CompletenessIndicator value={data?.completeness_score ?? 0} size={120} />
          <h2 className="mt-6 text-h2 text-foreground">
            Your profile is {Math.round(data?.completeness_score ?? 0)}% complete
          </h2>
          <p className="mt-2 text-body-lg text-muted-foreground">
            Great start. You can fill in more anytime.
          </p>
        </div>

        {/* Per-category breakdown */}
        <section className="mt-10 rounded-md border border-border bg-card p-4">
          <h3 className="mb-3 text-h4 text-foreground">By category</h3>
          {isLoading ? (
            <p className="text-body text-muted-foreground">Loading…</p>
          ) : (
            <ul className="space-y-3">
              {Object.entries(data?.completeness_by_category ?? {}).map(([key, value]) => (
                <li key={key}>
                  <div className="mb-1 flex items-center justify-between text-body">
                    <span className="font-medium text-foreground">
                      {CATEGORY_LABELS[key] ?? key}
                    </span>
                    <span className="text-muted-foreground">{Math.round(value)}%</span>
                  </div>
                  <Progress value={value} aria-label={`${CATEGORY_LABELS[key] ?? key} ${value}%`} />
                </li>
              ))}
            </ul>
          )}
        </section>

        {/* Recommended next */}
        <section className="mt-6 rounded-md border border-border bg-card p-4">
          <div className="flex items-start gap-3">
            <div className="rounded-md bg-brand-50 p-2">
              <Link2 className="h-5 w-5 text-brand-700" />
            </div>
            <div className="flex-1">
              <h3 className="text-h4 text-foreground">Connect your provider</h3>
              <p className="text-body text-muted-foreground">
                Pull in records from your hospital automatically. Coming in Phase 2.
              </p>
            </div>
            <Button variant="outline" size="sm" disabled>
              Coming soon
            </Button>
          </div>
        </section>

        <Button size="lg" className="mt-10 w-full" onClick={() => navigate("/dashboard")}>
          Go to my dashboard
        </Button>

        <Button
          variant="ghost"
          size="sm"
          className="mt-3 w-full"
          onClick={() => navigate("/onboarding")}
        >
          Start over
        </Button>
      </main>
    </div>
  );
}
