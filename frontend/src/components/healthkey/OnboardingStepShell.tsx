/**
 * OnboardingStepShell — wraps every step in /onboarding/*.
 * Per docs/patient-app-design.md §4.2 and §5.3.
 *
 *  - Top: progress bar + step counter + "Skip for now"
 *  - Body: arbitrary children
 *  - Bottom: Back + Continue
 *
 * "Skip for now" has equal visual weight to Continue per design principle #4.
 */
import { ReactNode } from "react";
import { Link } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";

interface Props {
  step: number;
  totalSteps: number;
  title?: string;
  description?: string;
  onContinue?: () => void;
  continueLabel?: string;
  continueDisabled?: boolean;
  backTo?: string;
  skipTo?: string;
  isSaving?: boolean;
  children: ReactNode;
}

export function OnboardingStepShell({
  step,
  totalSteps,
  title,
  description,
  onContinue,
  continueLabel = "Continue",
  continueDisabled = false,
  backTo,
  skipTo,
  isSaving,
  children,
}: Props) {
  const progress = (step / totalSteps) * 100;

  return (
    <div className="mx-auto flex min-h-screen max-w-xl flex-col px-4 py-6 sm:py-10">
      {/* Progress + skip */}
      <div className="mb-8 flex items-center gap-4">
        <div className="flex-1">
          <Progress value={progress} aria-label={`Step ${step} of ${totalSteps}`} />
          <p className="mt-2 text-caption text-muted-foreground">
            Step {step} of {totalSteps}
          </p>
        </div>
        {skipTo && (
          <Button asChild variant="ghost" size="sm">
            <Link to={skipTo}>Skip for now</Link>
          </Button>
        )}
      </div>

      {/* Heading */}
      {title && (
        <header className="mb-6">
          <h1 className="text-h1 text-foreground">{title}</h1>
          {description && (
            <p className="mt-2 text-body-lg text-muted-foreground">{description}</p>
          )}
        </header>
      )}

      {/* Body */}
      <main className="flex-1">{children}</main>

      {/* Auto-save indicator */}
      {isSaving && (
        <p className="mt-4 text-caption text-muted-foreground" aria-live="polite">
          Saving…
        </p>
      )}

      {/* Footer */}
      <footer className="mt-8 flex items-center justify-between border-t border-border pt-6">
        {backTo ? (
          <Button asChild variant="ghost">
            <Link to={backTo}>← Back</Link>
          </Button>
        ) : (
          <span />
        )}
        {onContinue && (
          <Button onClick={onContinue} disabled={continueDisabled}>
            {continueLabel} →
          </Button>
        )}
      </footer>
    </div>
  );
}
