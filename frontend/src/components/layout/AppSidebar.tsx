/**
 * AppSidebar — grouped navigation, modeled on the ht-phr portal shell.
 *
 * Desktop (≥ 1024px): fixed left sidebar. Mobile: slide-over drawer, opened
 * from the header hamburger; the overlay click and any nav click close it.
 */
import { FileText, FlaskConical, Home, Link2, User, X } from "lucide-react";
import { NavLink } from "react-router-dom";

type NavItem = {
  to: string;
  label: string;
  icon: typeof Home;
  end?: boolean;
  disabled?: boolean;
  hint?: string;
};

const NAV_GROUPS: { title: string; items: NavItem[] }[] = [
  {
    title: "Overview",
    items: [{ to: "/dashboard", label: "Dashboard", icon: Home, end: true }],
  },
  {
    title: "My Health",
    items: [
      { to: "/dashboard/records", label: "Records", icon: FileText },
      { to: "/dashboard/share", label: "Share", icon: Link2 },
      {
        to: "#",
        label: "Labs",
        icon: FlaskConical,
        disabled: true,
        hint: "Soon",
      },
    ],
  },
  {
    title: "Account",
    items: [{ to: "/dashboard/profile", label: "Profile", icon: User }],
  },
];

function NavItems({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <nav className="flex-1 space-y-6 overflow-y-auto px-3 py-4" aria-label="Primary">
      {NAV_GROUPS.map((group) => (
        <div key={group.title}>
          <p className="mb-1 px-3 text-caption font-semibold uppercase tracking-wide text-healthkey-text-tertiary">
            {group.title}
          </p>
          <div className="space-y-1">
            {group.items.map(({ to, label, icon: Icon, end, disabled, hint }) =>
              disabled ? (
                <span
                  key={label}
                  className="flex cursor-not-allowed items-center gap-3 rounded-md px-3 py-2 text-body font-medium text-healthkey-text-disabled"
                  aria-disabled="true"
                >
                  <Icon className="h-5 w-5" />
                  {label}
                  {hint && (
                    <span className="ml-auto rounded-full bg-healthkey-gray-100 px-2 py-0.5 text-caption text-healthkey-text-tertiary">
                      {hint}
                    </span>
                  )}
                </span>
              ) : (
                <NavLink
                  key={to}
                  to={to}
                  end={end}
                  onClick={onNavigate}
                  className={({ isActive }) =>
                    [
                      "flex items-center gap-3 rounded-md px-3 py-2 text-body font-medium transition-colors",
                      isActive
                        ? "bg-brand-50 text-brand-700"
                        : "text-healthkey-text-secondary hover:bg-healthkey-bg-active hover:text-healthkey-text-primary",
                    ].join(" ")
                  }
                >
                  <Icon className="h-5 w-5" />
                  {label}
                </NavLink>
              ),
            )}
          </div>
        </div>
      ))}
    </nav>
  );
}

function Wordmark() {
  return (
    <p className="text-h3 font-bold text-brand-700">
      Health<span className="text-healthkey-brand-alt">Key</span>
    </p>
  );
}

export function AppSidebar({
  mobileOpen,
  onClose,
}: {
  mobileOpen: boolean;
  onClose: () => void;
}) {
  return (
    <>
      {/* Desktop sidebar */}
      <aside className="hidden lg:flex lg:w-64 lg:shrink-0 lg:flex-col lg:border-r lg:border-healthkey-border-secondary lg:bg-healthkey-bg-secondary">
        <div className="flex h-16 items-center px-6">
          <Wordmark />
        </div>
        <NavItems />
      </aside>

      {/* Mobile drawer */}
      {mobileOpen && (
        <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true">
          <div
            className="absolute inset-0 bg-black/40"
            aria-hidden="true"
            onClick={onClose}
          />
          <aside className="absolute inset-y-0 left-0 flex w-72 flex-col bg-healthkey-bg-primary shadow-xl">
            <div className="flex h-16 items-center justify-between px-6">
              <Wordmark />
              <button
                type="button"
                onClick={onClose}
                aria-label="Close menu"
                className="rounded-md p-1 text-healthkey-text-secondary hover:bg-healthkey-bg-active"
              >
                <X className="h-5 w-5" />
              </button>
            </div>
            <NavItems onNavigate={onClose} />
          </aside>
        </div>
      )}
    </>
  );
}
