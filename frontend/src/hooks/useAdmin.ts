import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { listAdmins, setUserClaims } from "@/api/admin";
import { useAuth } from "@/contexts/AuthContext";
import type { AppUser } from "@/types/user";

export const adminKeys = {
  all: ["admins"] as const,
};

export function useAdmins() {
  return useQuery({
    queryKey: adminKeys.all,
    queryFn: listAdmins,
  });
}

export function useSetUserClaims() {
  const queryClient = useQueryClient();
  const { user, reload } = useAuth();

  return useMutation({
    mutationFn: ({
      userId,
      claims,
    }: {
      userId: number;
      claims: Partial<Record<"ADMIN" | "MEDICAL_RECORDS", boolean>>;
    }) => setUserClaims(userId, claims),
    onMutate: async ({ userId, claims }) => {
      await queryClient.cancelQueries({ queryKey: adminKeys.all });
      const previous = queryClient.getQueryData<AppUser[]>(adminKeys.all);
      queryClient.setQueryData<AppUser[]>(adminKeys.all, (old) =>
        old?.map((u) =>
          u.id === userId
            ? {
                ...u,
                claims: { ...u.claims, ...claims },
                is_admin: claims.ADMIN ?? u.is_admin,
                has_medical_records: claims.MEDICAL_RECORDS ?? u.has_medical_records,
              }
            : u,
        ),
      );
      return { previous };
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData(adminKeys.all, context.previous);
      }
    },
    onSettled: (_data, _err, { userId }) => {
      if (userId === user?.id) reload();
    },
  });
}
