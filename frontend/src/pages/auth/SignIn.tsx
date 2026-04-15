import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { Eye, EyeOff } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { useAuth } from "@/contexts/AuthContext";

interface FormValues {
  email: string;
  password: string;
}

export function SignIn() {
  const navigate = useNavigate();
  const { signIn } = useAuth();
  const [showPassword, setShowPassword] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<FormValues>();

  const onSubmit = async (values: FormValues) => {
    setServerError(null);
    try {
      await signIn(values.email, values.password);
      navigate("/dashboard");
    } catch {
      setServerError("Email or password didn't match. Try again.");
    }
  };

  return (
    <div className="mx-auto flex min-h-screen max-w-md flex-col justify-center px-4 py-10">
      <header className="mb-8 text-center">
        <p className="mb-8 text-h3 font-bold text-brand-700">HealthKey</p>
        <h1 className="text-h1 text-foreground">Welcome back</h1>
        <p className="mt-2 text-body-lg text-muted-foreground">Sign in to your account.</p>
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
              {...register("email", { required: "Email is required" })}
            />
            {errors.email && <p className="text-caption text-error-700">{errors.email.message}</p>}
          </div>

          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <div className="relative">
              <Input
                id="password"
                type={showPassword ? "text" : "password"}
                autoComplete="current-password"
                {...register("password", { required: "Password is required" })}
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
            {errors.password && (
              <p className="text-caption text-error-700">{errors.password.message}</p>
            )}
          </div>

          {serverError && (
            <div role="alert" className="rounded-md bg-error-50 p-3 text-body text-error-700">
              {serverError}
            </div>
          )}

          <Button type="submit" size="lg" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? "Signing in…" : "Sign in"}
          </Button>

          <p className="text-center text-body text-muted-foreground">
            Don't have an account?{" "}
            <Link to="/auth/sign-up" className="font-semibold text-brand-700 hover:underline">
              Create one
            </Link>
          </p>
        </form>
      </main>
    </div>
  );
}
