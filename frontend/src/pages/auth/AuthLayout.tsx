import type { ReactNode } from "react";
import HealthKeyLogo from "@/components/HealthKeyLogo";

interface AuthLayoutProps {
  heading: string;
  children: ReactNode;
}

export default function AuthLayout({ heading, children }: AuthLayoutProps) {
  return (
    <div className="flex min-h-svh items-center justify-center bg-background sm:bg-muted sm:px-4 sm:py-8">
      <div className="w-full max-w-sm space-y-6 p-6 sm:rounded-lg sm:bg-card sm:p-8 sm:shadow-card">
        <div className="flex justify-center">
          <HealthKeyLogo />
        </div>
        <h1 className="text-center text-xl font-semibold">{heading}</h1>
        {children}
      </div>
    </div>
  );
}
