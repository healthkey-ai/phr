import { useAuth } from "@/contexts/AuthContext";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { RoleBadge } from "@/components/ui/role-badge";

export default function AdminDashboardPage() {
  const { user } = useAuth();

  return (
    <div>
      <h1 className="text-xl font-semibold">Admin Dashboard</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Welcome, {user?.first_name || user?.email}
      </p>

      <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle>Your Role</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex gap-2">
              {user?.claims?.ADMIN && <RoleBadge role="ADMIN" />}
              {user?.claims?.MEDICAL_RECORDS && <RoleBadge role="MEDICAL_RECORDS" />}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
