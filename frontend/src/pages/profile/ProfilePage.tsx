import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/api/client";
import { useAuth } from "@/contexts/AuthContext";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Alert } from "@/components/ui/alert";
import { LoadingIndicator } from "@/components/ui/loading-indicator";

interface Profile {
  id: number;
  onboarding_step: string;
  details: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

const DETAIL_FIELDS: { key: string; label: string; type: string; placeholder?: string }[] = [
  { key: "dob", label: "Date of birth", type: "date" },
  { key: "gender", label: "Gender", type: "text", placeholder: "e.g. female" },
  { key: "conditions", label: "Conditions", type: "text", placeholder: "Comma-separated, e.g. hypertension" },
  { key: "medications", label: "Current medications", type: "text", placeholder: "Comma-separated" },
  { key: "allergies", label: "Drug allergies", type: "text", placeholder: "Comma-separated" },
];

export default function ProfilePage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const [saved, setSaved] = useState(false);
  const [draft, setDraft] = useState<Record<string, string> | null>(null);

  const { data: profile, isLoading } = useQuery({
    queryKey: ["profile"],
    queryFn: async () => (await api.get<Profile>("/profile/")).data,
  });

  const save = useMutation({
    mutationFn: async (details: Record<string, unknown>) =>
      (await api.patch<Profile>("/profile/", { details })).data,
    onSuccess: (data) => {
      queryClient.setQueryData(["profile"], data);
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    },
  });

  if (isLoading || !profile) {
    return <LoadingIndicator className="py-12" />;
  }

  const values =
    draft ??
    Object.fromEntries(
      DETAIL_FIELDS.map(({ key }) => [key, String(profile.details[key] ?? "")]),
    );

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    save.mutate({ ...profile.details, ...values });
  };

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <h1 className="text-lg font-medium text-foreground/70">Health Profile</h1>

      <Card>
        <CardHeader>
          <CardTitle>Account</CardTitle>
        </CardHeader>
        <CardContent className="space-y-1 text-sm">
          <p>
            <span className="text-muted-foreground">Name: </span>
            {user?.first_name} {user?.last_name}
          </p>
          <p>
            <span className="text-muted-foreground">Email: </span>
            {user?.email}
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Health details</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {DETAIL_FIELDS.map(({ key, label, type, placeholder }) => (
              <div key={key} className="space-y-2">
                <Label htmlFor={key}>{label}</Label>
                <Input
                  id={key}
                  type={type}
                  placeholder={placeholder}
                  value={values[key]}
                  onChange={(e) => setDraft({ ...values, [key]: e.target.value })}
                />
              </div>
            ))}
            {saved && <Alert variant="success">Profile saved.</Alert>}
            {save.isError && <Alert variant="destructive">Could not save. Try again.</Alert>}
            <Button type="submit" disabled={save.isPending}>
              {save.isPending ? "Saving..." : "Save"}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
