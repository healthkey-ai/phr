/**
 * AppHeader — top bar shared across portal pages: mobile menu trigger,
 * signed-in identity, and sign-out. Modeled on the ht-phr portal header.
 */
import { LogOut, Menu } from "lucide-react";

import { useAuth } from "@/contexts/AuthContext";

export function AppHeader({ onOpenMenu }: { onOpenMenu: () => void }) {
  const { user, signOut } = useAuth();

  return (
    <header className="flex h-16 shrink-0 items-center justify-between border-b border-healthkey-border-secondary bg-healthkey-bg-primary px-4 sm:px-6">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onOpenMenu}
          aria-label="Open menu"
          className="rounded-md p-2 text-healthkey-text-secondary hover:bg-healthkey-bg-active lg:hidden"
        >
          <Menu className="h-5 w-5" />
        </button>
        <p className="text-h4 font-bold text-brand-700 lg:hidden">HealthKey</p>
      </div>

      <div className="flex items-center gap-4">
        {user && (
          <span className="hidden text-body text-healthkey-text-secondary sm:block">
            {user.email}
          </span>
        )}
        <button
          type="button"
          onClick={signOut}
          className="flex items-center gap-2 rounded-md border border-healthkey-border-secondary px-3 py-1.5 text-body font-medium text-healthkey-text-secondary transition-colors hover:bg-healthkey-bg-active hover:text-healthkey-text-primary"
        >
          <LogOut className="h-4 w-4" />
          Sign out
        </button>
      </div>
    </header>
  );
}
