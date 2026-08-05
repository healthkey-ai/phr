import { cn } from "@/lib/utils";

interface RoleBadgeProps {
  role: "ADMIN" | "MEDICAL_RECORDS";
  className?: string;
  label?: string;
}

export function RoleBadge({ role, className, label }: RoleBadgeProps) {
  if (role === "ADMIN") {
    return (
      <span className={cn("rounded-full bg-green-900/20 px-2.5 py-0.5 text-xs font-medium text-green-300", className)}>
        {label || "ADMIN"}
      </span>
    );
  }

  if (role === "MEDICAL_RECORDS") {
    return (
      <span className={cn("rounded-full bg-blue-600/10 px-2.5 py-0.5 text-xs font-medium text-blue-100", className)}>
        {label || "MEDICAL_RECORDS"}
      </span>
    );
  }

  return null;
}
