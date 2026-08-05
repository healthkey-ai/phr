/**
 * Sign Up — /signup
 * Per docs/patient-app-design.md §5.1.
 *
 * Hierarchy: Brand → "Create your account" → email/password → CTA → terms.
 * No marketing copy. No "trusted by" logos. Restraint signals seriousness.
 */
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { Eye, EyeOff } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/contexts/AuthContext";

interface FormValues {
  email: string;
  password: string;
  agreeTerms: boolean;
}

function passwordStrength(pw: string): { score: 0 | 1 | 2 | 3 | 4; label: string } {
  let score = 0;
  if (pw.length >= 8) score++;
  if (/[A-Z]/.test(pw)) score++;
  if (/[0-9]/.test(pw)) score++;
  if (/[^A-Za-z0-9]/.test(pw)) score++;
  const label = ["Too weak", "Weak", "Okay", "Good", "Strong"][score];
  return { score: score as 0 | 1 | 2 | 3 | 4, label };
}

export function SignUp() {
  const navigate = useNavigate();
  const { signUp } = useAuth();
  const [showPassword, setShowPassword] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>({ defaultValues: { agreeTerms: false } });

  // Register the controlled checkbox so RHF tracks its required validation.
  // (Radix Checkbox isn't a native input, so we wire it via setValue.)
  const agreeTerms = watch("agreeTerms");

  const password = watch("password", "");
  const strength = passwordStrength(password);

  const onSubmit = async (values: FormValues) => {
    setServerError(null);
    try {
      await signUp(values.email, values.password);
      navigate("/onboarding");
    } catch (err: unknown) {
      const e = err as { response?: { data?: Record<string, string[] | string> } };
      const data = e.response?.data;
      if (data?.email) setServerError(`Email: ${Array.isArray(data.email) ? data.email[0] : data.email}`);
      else if (data?.password) setServerError(`Password: ${Array.isArray(data.password) ? data.password[0] : data.password}`);
      else setServerError("Couldn't create your account. Try again.");
    }
  };

  return (
    <div className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-4 py-10">
      <header className="mb-8 text-center">
        <p className="mb-8 text-h3 font-bold text-brand-700">HealthKey</p>
        <h1 className="text-h1 text-foreground">Create your account</h1>
        <p className="mt-2 text-body-lg text-muted-foreground">
          Take control of your health record.
        </p>
      </header>

      <main id="main">
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-5" noValidate>
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              aria-invalid={errors.email ? "true" : "false"}
              aria-describedby={errors.email ? "email-error" : undefined}
              {...register("email", {
                required: "Email is required",
                pattern: { value: /^[^\s@]+@[^\s@]+\.[^\s@]+$/, message: "Enter a valid email" },
              })}
            />
            {errors.email && (
              <p id="email-error" className="text-caption text-error-700">
                {errors.email.message}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <div className="relative">
              <Input
                id="password"
                type={showPassword ? "text" : "password"}
                autoComplete="new-password"
                aria-invalid={errors.password ? "true" : "false"}
                aria-describedby={errors.password ? "password-error" : "password-help"}
                {...register("password", {
                  required: "Password is required",
                  minLength: { value: 8, message: "Use at least 8 characters" },
                })}
              />
              <button
                type="button"
                onClick={() => setShowPassword((s) => !s)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
              </button>
            </div>

            {/* Strength meter */}
            {password && (
              <div className="space-y-1">
                <div className="flex h-1.5 gap-1">
                  {[1, 2, 3, 4].map((i) => (
                    <div
                      key={i}
                      className={`flex-1 rounded-sm ${
                        i <= strength.score
                          ? strength.score >= 3
                            ? "bg-success-700"
                            : strength.score >= 2
                              ? "bg-warning-700"
                              : "bg-error-700"
                          : "bg-muted"
                      }`}
                    />
                  ))}
                </div>
                <p className="text-caption text-muted-foreground" aria-live="polite">
                  {strength.label} · 8+ chars · uppercase · number · special
                </p>
              </div>
            )}
            {!password && (
              <p id="password-help" className="text-caption text-muted-foreground">
                8+ chars · uppercase · number · special
              </p>
            )}
            {errors.password && (
              <p id="password-error" className="text-caption text-error-700">
                {errors.password.message}
              </p>
            )}
          </div>

          <div className="flex items-start gap-3">
            <Checkbox
              id="terms"
              className="mt-0.5"
              checked={agreeTerms}
              onCheckedChange={(c) =>
                setValue("agreeTerms", Boolean(c), { shouldValidate: true })
              }
              aria-invalid={errors.agreeTerms ? "true" : "false"}
            />
            <input
              type="hidden"
              {...register("agreeTerms", { required: "Please agree to continue" })}
            />
            <Label htmlFor="terms" className="text-base font-normal text-foreground">
              I agree to the{" "}
              <a href="/terms" className="text-healthkey-link-primary underline">Terms</a>
              {" "}and{" "}
              <a href="/privacy" className="text-healthkey-link-primary underline">Privacy Policy</a>
            </Label>
          </div>
          {errors.agreeTerms && (
            <p className="text-caption text-error-700">{errors.agreeTerms.message}</p>
          )}

          {serverError && (
            <div role="alert" className="rounded-md bg-error-50 p-3 text-body text-error-700">
              {serverError}
            </div>
          )}

          <Button type="submit" size="lg" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? "Creating account…" : "Create account"}
          </Button>

          <p className="text-center text-body text-muted-foreground">
            Already have an account?{" "}
            <Link to="/login" className="font-semibold text-brand-700 hover:underline">
              Sign in
            </Link>
          </p>
        </form>
      </main>
    </div>
  );
}
