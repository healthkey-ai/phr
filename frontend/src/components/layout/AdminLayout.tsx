import { NavLink, Outlet } from "react-router-dom";
import HealthKeyLogo from "@/components/HealthKeyLogo";
import AppHeader from "./AppHeader";

interface NavItem {
  label: string;
  to: string;
}

interface AdminLayoutProps {
  title: string;
  navItems: NavItem[];
}

export default function AdminLayout({ title, navItems }: AdminLayoutProps) {
  return (
    <div className="flex min-h-svh bg-muted">
      {/* Sidebar */}
      {/* max-sm:hidden, not bare `hidden` — see AppSidebar.tsx: remote-injected
          CSS contains .hidden and would override sm:block by document order. */}
      <aside className="max-sm:hidden sticky top-0 h-svh w-60 shrink-0 border-r border-sidebar-border bg-sidebar text-sidebar-foreground sm:block">
        <div className="flex h-14 items-center border-b border-sidebar-border px-4">
          <HealthKeyLogo showName={false} className="text-chrome-logo" />
          <span className="ml-2 text-sm font-semibold text-sidebar-foreground">{title}</span>
        </div>
        <nav className="space-y-1 p-3">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to.split("/").length <= 3}
              className={({ isActive }) =>
                `block rounded-control px-3 py-2 text-sm transition-colors ${
                  isActive
                    ? "bg-sidebar-active/10 font-medium text-sidebar-active-foreground"
                    : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>

      {/* Main content */}
      <div className="flex flex-1 flex-col">
        <AppHeader layout="admin" title={title} />
        <main className="flex-1 px-4 py-6 sm:px-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
