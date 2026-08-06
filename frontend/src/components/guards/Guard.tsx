import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "@/contexts/AuthContext";
import type { ReactNode } from "react";
import type { AppUser } from "@/types/user";

interface GuardProps {
  children: ReactNode;
  allow: (user: AppUser | null) => boolean;
  redirectTo?: string;
}

export default function Guard({ children, allow, redirectTo = "/login" }: GuardProps) {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return null;
  if (!allow(user)) {
    if (redirectTo === "/login") {
      // Preserve the deep link so login can return the user to where they
      // were headed instead of dumping them on the dashboard.
      return <Navigate to="/login" state={{ from: location }} replace />;
    }
    // Public-only pages (login/signup) bounce authenticated users to the
    // originally-requested location when one was stashed by the redirect
    // above — this wins even if this Navigate races LoginPage's own
    // post-login navigate(from).
    const from = (location.state as { from?: { pathname: string } } | null)?.from;
    return <Navigate to={from?.pathname ?? redirectTo} replace />;
  }
  return children;
}
