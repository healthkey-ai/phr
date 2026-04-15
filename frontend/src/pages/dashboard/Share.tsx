/**
 * Dashboard Share tab — /dashboard/share
 * Per docs/patient-app-design.md §5.10.
 *
 * Phase 1 stub. Full sharing (access grants, QR codes, SMART Health Links) is Phase 3.
 */
import { Link2 } from "lucide-react";

import { Card, CardContent } from "@/components/ui/card";

export function Share() {
  return (
    <div className="mx-auto max-w-2xl p-4 sm:p-6 lg:p-10">
      <h1 className="mb-2 text-h1 text-foreground">Share your record</h1>
      <p className="mb-6 text-body-lg text-muted-foreground">
        Create time-limited access for a doctor or caregiver. They'll see only what you choose. You
        can revoke access anytime.
      </p>

      <Card>
        <CardContent className="p-10 text-center">
          <div className="mx-auto mb-4 inline-flex h-12 w-12 items-center justify-center rounded-full bg-brand-50">
            <Link2 className="h-6 w-6 text-brand-700" />
          </div>
          <p className="text-h4 text-foreground">Sharing is coming in Phase 3</p>
          <p className="mt-2 text-body text-muted-foreground">
            Time-limited access grants, scoped FHIR bundles, QR codes, and SMART Health Links will
            land in the next phase.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
