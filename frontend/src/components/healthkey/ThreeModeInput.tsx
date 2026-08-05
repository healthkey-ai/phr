/**
 * ThreeModeInput — the defining UI pattern for data collection steps.
 * Per docs/patient-app-design.md §4.2 (component) and §5.3 (in-context).
 *
 * Three keyboard-focusable cards: Type it / Upload / Connect EHR.
 * Phase 1: only "Type it in" is wired up. Upload + Connect are placeholders
 * (Phase 2). Cards still render so the affordance is visible.
 */
import type { ReactElement } from "react";
import { FileText, Link2, Pencil } from "lucide-react";

type Mode = "manual" | "upload" | "ehr";

interface Props {
  active: Mode;
  onChange: (mode: Mode) => void;
  disabled?: { upload?: boolean; ehr?: boolean };
}

export function ThreeModeInput({ active, onChange, disabled = {} }: Props) {
  const items: { mode: Mode; label: string; icon: ReactElement; hint?: string; disabled?: boolean }[] = [
    { mode: "manual", label: "Type it in", icon: <Pencil className="h-6 w-6" /> },
    {
      mode: "upload",
      label: "Upload documents",
      icon: <FileText className="h-6 w-6" />,
      hint: "Coming soon",
      disabled: disabled.upload ?? true,
    },
    {
      mode: "ehr",
      label: "Connect your EHR",
      icon: <Link2 className="h-6 w-6" />,
      hint: "Coming soon",
      disabled: disabled.ehr ?? true,
    },
  ];

  return (
    <div className="mb-8">
      <p className="mb-3 text-body font-semibold text-foreground">How would you like to add this?</p>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {items.map((item) => {
          const isActive = active === item.mode;
          return (
            <button
              key={item.mode}
              type="button"
              onClick={() => !item.disabled && onChange(item.mode)}
              disabled={item.disabled}
              aria-pressed={isActive}
              className={[
                "flex flex-col items-center gap-2 rounded-md border p-4 text-center transition-colors",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-700 focus-visible:ring-offset-2",
                isActive
                  ? "border-brand-700 bg-brand-50 text-brand-700"
                  : "border-border bg-background text-foreground hover:bg-muted",
                item.disabled && "cursor-not-allowed opacity-50",
              ]
                .filter(Boolean)
                .join(" ")}
            >
              {item.icon}
              <span className="text-body font-semibold">{item.label}</span>
              {item.hint && <span className="text-caption text-muted-foreground">{item.hint}</span>}
            </button>
          );
        })}
      </div>
    </div>
  );
}
