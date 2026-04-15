/**
 * Onboarding Welcome — /onboarding
 * Per docs/patient-app-design.md §5.2.
 *
 * Hierarchy: greeting → reassurance → action.
 * "You can skip" appears here to lower anxiety upfront.
 */
import { useNavigate } from "react-router-dom";

import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { useAuth } from "@/contexts/AuthContext";

export function Welcome() {
  const navigate = useNavigate();
  const { user } = useAuth();
  const greetingName = user?.email?.split("@")[0] ?? "there";

  return (
    <div className="mx-auto flex min-h-screen max-w-xl flex-col px-4 py-6 sm:py-10">
      <div className="mb-12">
        <Progress value={12.5} aria-label="Step 1 of 8" />
        <p className="mt-2 text-caption text-muted-foreground">Step 1 of 8</p>
      </div>

      <main id="main" className="flex flex-1 flex-col items-center justify-center text-center">
        <h1 className="text-h1 text-foreground">Welcome, {greetingName}</h1>
        <p className="mt-6 max-w-md text-body-lg text-muted-foreground">
          We'll help you build a complete picture of your health. This takes about 5 minutes.
        </p>
        <p className="mt-3 max-w-md text-body-lg text-muted-foreground">
          You can skip any step. Nothing is required.
        </p>

        <Button
          size="lg"
          className="mt-10"
          onClick={() => navigate("/onboarding/demographics")}
        >
          Continue
        </Button>

        <Button
          variant="link"
          className="mt-4"
          onClick={() => navigate("/dashboard")}
        >
          Skip onboarding for now
        </Button>
      </main>
    </div>
  );
}
