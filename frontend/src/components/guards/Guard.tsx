import { Navigate } from "react-router-dom";
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
  if (loading) return null;
  if (!allow(user)) return <Navigate to={redirectTo} replace />;
  return children;
}
