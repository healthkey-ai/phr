/**
 * DashboardShell — wraps Home/Records/Share/Profile tabs.
 * Per docs/patient-app-design.md §3.2.
 *
 *  - Mobile (≤ 768px): bottom nav bar, fixed
 *  - Tablet (769–1023px): top nav bar
 *  - Desktop (≥ 1024px): left sidebar
 */
import { Bell, FileText, Home, Link2, User } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";

const TABS = [
  { to: "/dashboard", label: "Home", icon: Home, end: true },
  { to: "/dashboard/records", label: "Records", icon: FileText, end: false },
  { to: "/dashboard/share", label: "Share", icon: Link2, end: false },
  { to: "/dashboard/profile", label: "Profile", icon: User, end: false },
];

export function DashboardShell() {
  return (
    <div className="flex min-h-screen flex-col lg:flex-row">
      {/* Desktop sidebar */}
      <aside className="hidden lg:flex lg:w-64 lg:flex-col lg:border-r lg:border-border lg:bg-muted/30">
        <div className="flex h-16 items-center px-6">
          <p className="text-h3 font-bold text-brand-700">HealthKey</p>
        </div>
        <nav className="flex-1 space-y-1 px-3" aria-label="Primary">
          {TABS.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                [
                  "flex items-center gap-3 rounded-md px-3 py-2 text-body font-medium",
                  isActive
                    ? "bg-brand-50 text-brand-700"
                    : "text-foreground hover:bg-muted",
                ].join(" ")
              }
            >
              <Icon className="h-5 w-5" />
              {label}
            </NavLink>
          ))}
        </nav>
      </aside>

      {/* Mobile/tablet top bar */}
      <header className="flex h-14 items-center justify-between border-b border-border bg-background px-4 lg:hidden">
        <p className="text-h4 font-bold text-brand-700">HealthKey</p>
        <button
          type="button"
          className="p-2 text-muted-foreground hover:text-foreground"
          aria-label="Notifications"
        >
          <Bell className="h-5 w-5" />
        </button>
      </header>

      {/* Main content */}
      <main id="main" className="flex-1 overflow-y-auto pb-20 lg:pb-0">
        <Outlet />
      </main>

      {/* Mobile bottom nav */}
      <nav
        aria-label="Primary"
        className="fixed bottom-0 left-0 right-0 grid grid-cols-4 border-t border-border bg-background lg:hidden"
      >
        {TABS.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              [
                "flex flex-col items-center justify-center gap-1 py-2 text-caption font-medium",
                isActive ? "text-brand-700" : "text-muted-foreground",
              ].join(" ")
            }
          >
            <Icon className="h-5 w-5" />
            {label}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
