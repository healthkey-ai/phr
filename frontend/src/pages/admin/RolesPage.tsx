import { useAdmins, useSetUserClaims } from "@/hooks/useAdmin";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "@/components/ui/table";
import { Checkbox } from "@/components/ui/checkbox";
import { LoadingIndicator } from "@/components/ui/loading-indicator";
import type { AppUser } from "@/types/user";

export default function RolesPage() {
  const { data: admins, isLoading } = useAdmins();
  const mutation = useSetUserClaims();

  const toggleClaim = (user: AppUser, claim: "ADMIN" | "MEDICAL_RECORDS") => {
    const current = claim === "ADMIN" ? user.claims.ADMIN : user.claims.MEDICAL_RECORDS;
    mutation.mutate({ userId: user.id, claims: { [claim]: !current } });
  };

  if (isLoading) {
    return <LoadingIndicator className="py-8" />;
  }

  return (
    <div>
      <h1 className="text-xl font-semibold">Roles</h1>
      <p className="mt-1 text-sm text-muted-foreground">
        Manage <span className="font-medium text-foreground">Admin</span> and <span className="font-medium text-foreground">Medical Records</span> roles for portal users.
      </p>

      <div className="mt-6">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Email</TableHead>
              <TableHead>Name</TableHead>
              <TableHead className="text-center">Admin</TableHead>
              <TableHead className="text-center">Medical Records</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody className={mutation.isPending ? "pointer-events-none" : undefined}>
            {admins?.map((user) => (
              <TableRow key={user.id}>
                <TableCell>{user.email}</TableCell>
                <TableCell className="text-muted-foreground">
                  {user.first_name} {user.last_name}
                </TableCell>
                <TableCell className="text-center">
                  <Checkbox
                    checked={user.claims.ADMIN}
                    onChange={() => toggleClaim(user, "ADMIN")}
                  />
                </TableCell>
                <TableCell className="text-center">
                  <Checkbox
                    checked={user.claims.MEDICAL_RECORDS}
                    onChange={() => toggleClaim(user, "MEDICAL_RECORDS")}
                  />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        {admins?.length === 0 && (
          <p className="py-8 text-center text-sm text-muted-foreground">
            No users found.
          </p>
        )}
      </div>
    </div>
  );
}
