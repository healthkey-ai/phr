import { cn } from "@/lib/utils";
interface HealthKeyLogoProps {
  className?: string;
  showName?: boolean;
}

export default function HealthKeyLogo({ className = "", showName = true }: HealthKeyLogoProps) {
  return (
    // cn(), not a template string: the mark sits on the branded header and on
    // the admin sidebar, where it has to take that surface's foreground. With
    // string concatenation both colour classes survive and which one wins is
    // decided by stylesheet order, so the caller's override was ignored —
    // under a brand whose --brand-700 matches the header, the wordmark
    // disappeared into it.
    <a href="/" className={cn("flex items-center gap-2 text-brand-700 no-underline", className)}>
      <svg
        width="28"
        height="28"
        viewBox="0 0 28 28"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="shrink-0"
        aria-hidden="true"
      >
        <rect x="2" y="2" width="24" height="24" rx="6" fill="currentColor" />
        <path
          d="M9 8v12M19 8v12M9 14h10"
          stroke="white"
          strokeWidth="2.5"
          strokeLinecap="round"
        />
      </svg>
      {showName && (
        <span className="text-lg font-bold leading-tight">
          Health<span className="text-brand-alt">Key</span>
        </span>
      )}
    </a>
  );
}
