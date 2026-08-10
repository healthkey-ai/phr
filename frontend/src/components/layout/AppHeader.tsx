import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { RoleBadge } from "@/components/ui/role-badge";
import { cn } from "@/lib/utils";

interface AppHeaderProps {
  layout: "app" | "admin";
  title?: string;
  className?: string;
  children?: React.ReactNode;
}

export default function AppHeader({ layout, title, className, children }: AppHeaderProps) {
  const { user, logout } = useAuth();

  return (
    <header className={cn("flex h-14 items-center border-b border-header-border bg-header text-header-foreground px-4 sm:px-6", className)}>
      <div className="flex w-full items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          {children}
          {layout === "admin" && (
            <>
              <span className="text-sm font-semibold sm:hidden">{title}</span>
              <div className="max-sm:hidden sm:block" />
            </>
          )}
        </div>

        <div className="flex items-center gap-2 sm:gap-4">
          <span className="max-md:hidden text-sm text-muted-foreground md:inline">
            {user?.first_name || user?.last_name
              ? `${user.first_name ?? ""} ${user.last_name ?? ""}`.trim()
              : user?.email}
          </span>

          {layout === "admin" && user?.claims?.MEDICAL_RECORDS && (
            <RoleBadge role="MEDICAL_RECORDS" label="Medical Records" />
          )}

          <Button variant="outline" size="sm" onClick={logout}>
            Sign out
          </Button>
        </div>
      </div>
    </header>
  );
}
