import { useAuth } from "@/contexts/AuthContext";

export default function DashboardPage() {
  const { user } = useAuth();

  return (
    <>
      <h1 className="text-lg font-medium text-foreground/70">Home</h1>
      <p className="mt-2 text-muted-foreground">
        Welcome back, {user?.first_name || user?.email}
      </p>
    </>
  );
}
