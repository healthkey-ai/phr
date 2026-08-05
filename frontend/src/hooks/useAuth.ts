import { useMutation } from "@tanstack/react-query";
import { loginWithEmail, registerWithEmail, logout } from "@/api/auth";

export function useLoginWithEmail() {
  return useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) =>
      loginWithEmail(email, password),
  });
}

export function useRegisterWithEmail() {
  return useMutation({
    mutationFn: ({
      email,
      password,
      firstName,
      lastName,
    }: {
      email: string;
      password: string;
      firstName: string;
      lastName: string;
    }) => registerWithEmail(email, password, firstName, lastName),
  });
}

export function useLogout() {
  return useMutation({ mutationFn: logout });
}
