import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useLoginWithEmail } from "@/hooks/useAuth";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PasswordInput } from "@/components/ui/password-input";
import { Label } from "@/components/ui/label";
import { Alert } from "@/components/ui/alert";
import AuthLayout from "./AuthLayout";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();
  const { reload } = useAuth();

  const loginEmail = useLoginWithEmail();

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    setError("");
    loginEmail.mutate(
      { email, password },
      {
        onSuccess: async () => { await reload(); navigate("/dashboard"); },
        onError: () => setError("Sign-in failed. Check your email and password."),
      },
    );
  };

  return (
    <AuthLayout heading="Sign in to your account">
      <form onSubmit={handleSubmit} className="space-y-4">
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
            placeholder="Enter your password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>
        {error && <Alert variant="destructive">{error}</Alert>}
        <Button type="submit" className="w-full" disabled={loginEmail.isPending}>
          {loginEmail.isPending ? "Signing in..." : "Sign in"}
        </Button>
      </form>

      <p className="text-center text-sm text-muted-foreground">
        Don't have an account?{" "}
        <Link to="/signup" className="font-medium text-primary underline-offset-4 hover:underline">
          Sign up
        </Link>
      </p>
    </AuthLayout>
  );
}
