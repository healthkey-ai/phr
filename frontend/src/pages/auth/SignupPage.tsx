import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useRegisterWithEmail } from "@/hooks/useAuth";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PasswordInput } from "@/components/ui/password-input";
import { Label } from "@/components/ui/label";
import { Alert } from "@/components/ui/alert";
import AuthLayout from "./AuthLayout";

export default function SignupPage() {
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();
  const { reload } = useAuth();

  const register = useRegisterWithEmail();

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    setError("");
    register.mutate(
      { email, password, firstName, lastName },
      {
        onSuccess: async () => { await reload(); navigate("/dashboard"); },
        onError: (err) => {
          // Only DRF field-error objects carry a useful message; a 500's
          // HTML body is a string, and Object.values on a string yields
          // characters (the infamous empty-looking "<" alert).
          const detail = (err as { response?: { data?: unknown } }).response?.data;
          let firstMessage: unknown;
          if (detail && typeof detail === "object" && !Array.isArray(detail)) {
            firstMessage = Object.values(detail as Record<string, unknown>).flat()[0];
          }
          setError(
            typeof firstMessage === "string" && firstMessage.length > 1
              ? firstMessage
              : "Registration failed. Please try again.",
          );
        },
      },
    );
  };

  return (
    <AuthLayout heading="Create your account">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="firstName">First name</Label>
          <Input
            id="firstName"
            type="text"
            placeholder="First name"
            value={firstName}
            onChange={(e) => setFirstName(e.target.value)}
            required
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="lastName">Last name</Label>
          <Input
            id="lastName"
            type="text"
            placeholder="Last name"
            value={lastName}
            onChange={(e) => setLastName(e.target.value)}
            required
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="email">Email</Label>
          <Input
            id="email"
            type="email"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="password">Password</Label>
          <PasswordInput
            id="password"
            placeholder="8+ characters"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            minLength={8}
            required
          />
        </div>
        {error && <Alert variant="destructive">{error}</Alert>}
        <Button type="submit" className="w-full" disabled={register.isPending}>
          {register.isPending ? "Creating account..." : "Sign up"}
        </Button>
      </form>

      <p className="text-center text-sm text-muted-foreground">
        Already have an account?{" "}
        <Link to="/login" className="font-medium text-primary underline-offset-4 hover:underline">
          Sign in
        </Link>
      </p>
    </AuthLayout>
  );
}
