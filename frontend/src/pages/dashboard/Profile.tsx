/**
 * Dashboard Profile tab — /dashboard/profile
 * Per docs/patient-app-design.md §5.13.
 */
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/contexts/AuthContext";
import { usePatientInfo } from "@/features/patient-profile/api";

export function Profile() {
  const { user, signOut } = useAuth();
  const { data: patient } = usePatientInfo();

  return (
    <div className="mx-auto max-w-2xl p-4 sm:p-6 lg:p-10">
      <h1 className="mb-6 text-h1 text-foreground">Profile</h1>

      <Card className="mb-6">
        <CardContent className="p-6">
          {patient?.first_name && (
            <p className="text-h4 text-foreground">
              {patient.first_name} {patient.last_name}
            </p>
          )}
          <p className="text-body text-muted-foreground">{user?.email}</p>
          <p className="mt-2 text-caption text-muted-foreground">
            Identity level: {user?.identity_level ?? "unverified"}
          </p>
        </CardContent>
      </Card>

      <section className="mb-6">
        <h2 className="mb-3 text-h3 text-foreground">Connected accounts</h2>
        <Card>
          <CardContent className="p-6">
            <p className="text-body text-muted-foreground">
              EHR connections (Epic, Cerner, athenahealth) coming in Phase 2.
            </p>
          </CardContent>
        </Card>
      </section>

      <section className="mb-6">
        <h2 className="mb-3 text-h3 text-foreground">Settings</h2>
        <Card>
          <CardContent className="p-6">
            <p className="text-body text-muted-foreground">
              Notifications, biometric lock, and theme settings coming soon.
            </p>
          </CardContent>
        </Card>
      </section>

      <section className="mb-6">
        <h2 className="mb-3 text-h3 text-foreground">Your data</h2>
        <Card>
          <CardContent className="p-6">
            <p className="text-body text-muted-foreground">
              FHIR R4 / OMOP / PDF export coming in Phase 4.
            </p>
          </CardContent>
        </Card>
      </section>

      <Button variant="outline" className="w-full" onClick={signOut}>
        Sign out
      </Button>
    </div>
  );
}
