import { useState } from "react";
import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  UserCircle,
  TestTubes,
  Upload,
  FileHeart,
  Search,
  Microscope,
  Link2,
  ChevronDown,
  Menu,
  Settings,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { cn } from "@/lib/utils";

interface NavItem {
  label: string;
  to: string;
  icon: LucideIcon;
  disabled?: boolean;
}

interface NavGroup {
  label: string;
  items: NavItem[];
}

const navGroups: NavGroup[] = [
  {
    label: "Home",
    items: [
      { label: "Home", to: "/dashboard", icon: LayoutDashboard },
    ],
  },
  {
    label: "My Health",
    items: [
      // Only items with a connected federated module are enabled. The labs
      // routes stay registered in App.tsx so deep links keep working during
      // the hk-labs transition; /connect/records, /treatments, /trials and
      // /share have NO routes yet — register them before enabling the item,
      // or the catch-all silently bounces users to /dashboard.
      { label: "Health Profile", to: "/patient/record", icon: UserCircle },
      { label: "Connect Records", to: "/connect/records", icon: FileHeart, disabled: true },
      // Uploads come from hk-labs' remote — enabled only where that remote
      // is configured (VITE_LABS_REMOTE_URL), so production stays "Coming
      // soon" until hk-labs is deployed.
      {
        label: "Upload Lab Reports",
        to: "/labs/uploads",
        icon: Upload,
        disabled: !import.meta.env.VITE_LABS_REMOTE_URL,
      },
      // Lab Results is served by promop's remote (OMOP measurements).
      { label: "Lab Results", to: "/labs/results", icon: TestTubes },
      // soc's remote; enabled wherever it is configured, same rule as uploads.
      {
        label: "Find Treatments",
        to: "/treatments",
        icon: Search,
        disabled: !import.meta.env.VITE_SOC_REMOTE_URL,
      },
      { label: "Find Trials", to: "/trials", icon: Microscope, disabled: true },
    ],
  },
  {
    label: "Sharing",
    items: [
      { label: "Share My Record", to: "/share", icon: Link2, disabled: true },
    ],
  },
];

function NavGroupSection({ group, iconOnly }: { group: NavGroup; iconOnly: boolean }) {
  const [open, setOpen] = useState(true);

  return (
    <div>
      {!iconOnly && (
        <button
          onClick={() => setOpen(!open)}
          className="flex w-full items-center justify-between px-3 py-1.5 text-xs font-semibold uppercase tracking-wider text-muted-foreground hover:text-foreground"
        >
          {group.label}
          <ChevronDown className={cn("h-3.5 w-3.5 transition-transform", !open && "-rotate-90")} />
        </button>
      )}
      {(iconOnly || open) && (
        <nav className={cn("mt-0.5 space-y-0.5", iconOnly ? "px-1" : "px-2")}>
          {group.items.map((item) => {
            const Icon = item.icon;
            if (item.disabled) {
              return (
                <span
                  key={item.to}
                  aria-disabled="true"
                  title={iconOnly ? item.label : "Coming soon"}
                  className={cn(
                    "flex items-center rounded text-muted-foreground/50 cursor-not-allowed",
                    iconOnly ? "justify-center p-2" : "gap-2.5 px-2.5 py-1.5 text-sm"
                  )}
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  {!iconOnly && item.label}
                </span>
              );
            }
            return (
              <NavLink
                key={item.to}
                to={item.to}
                end
                title={iconOnly ? item.label : undefined}
                className={({ isActive }) =>
                  cn(
                    "flex items-center rounded transition-colors",
                    iconOnly ? "justify-center p-2" : "gap-2.5 px-2.5 py-1.5 text-sm",
                    isActive
                      ? "bg-primary/10 font-medium text-primary"
                      : "text-muted-foreground hover:bg-accent hover:text-foreground"
                  )
                }
              >
                <Icon className="h-4 w-4 shrink-0" />
                {!iconOnly && item.label}
              </NavLink>
            );
          })}
        </nav>
      )}
    </div>
  );
}

interface AppSidebarProps {
  expanded: boolean;
  onToggle: () => void;
  mobileOpen: boolean;
  onMobileClose: () => void;
}

export default function AppSidebar({ expanded, onToggle, mobileOpen, onMobileClose }: AppSidebarProps) {
  const { user } = useAuth();

  return (
    <>
      {/* Backdrop for mobile */}
      {mobileOpen && (
        <div className="fixed inset-0 z-30 bg-black/40 lg:hidden" onClick={onMobileClose} />
      )}

      {/* Mobile overlay sidebar — always full width */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-border bg-card transition-transform duration-200 lg:hidden",
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex h-14 items-center border-b border-border px-4">
          <button onClick={onMobileClose} className="rounded p-1 text-muted-foreground hover:bg-accent">
            <Menu className="h-5 w-5" />
          </button>
        </div>
        <div className="flex-1 space-y-4 overflow-y-auto py-3">
          {navGroups.map((group) => (
            <NavGroupSection key={group.label} group={group} iconOnly={false} />
          ))}
        </div>
        <div className="border-t border-border p-3">
          {user?.claims?.ADMIN && (
            <NavLink
              to="/admin"
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-2.5 rounded px-2.5 py-1.5 text-sm transition-colors",
                  isActive
                    ? "bg-primary/10 font-medium text-primary"
                    : "text-muted-foreground hover:bg-accent hover:text-foreground"
                )
              }
            >
              <Settings className="h-4 w-4 shrink-0" />
              Admin Panel
            </NavLink>
          )}
        </div>
      </aside>

      {/* Desktop sidebar — expands/collapses to icon-only. */}
      <aside
        className={cn(
          // max-lg:hidden (not bare `hidden`): federated remotes inject their
          // compiled Tailwind into our <head> after our stylesheet, and a
          // remote's `.hidden` rule outranks our `lg:flex` by document order,
          // permanently hiding the sidebar. Media-scoped variants can't collide.
          "max-lg:hidden lg:flex shrink-0 flex-col border-r border-border bg-card transition-all duration-200",
          expanded ? "w-64" : "w-14"
        )}
      >
        <div className={cn("flex h-14 items-center border-b border-border", expanded ? "px-4" : "justify-center")}>
          <button onClick={onToggle} className="rounded p-1 text-muted-foreground hover:bg-accent">
            <Menu className="h-5 w-5" />
          </button>
        </div>
        <div className={cn("flex-1 overflow-y-auto py-3", expanded ? "space-y-4" : "space-y-2")}>
          {navGroups.map((group) => (
            <NavGroupSection key={group.label} group={group} iconOnly={!expanded} />
          ))}
        </div>
        <div className={cn("border-t border-border", expanded ? "p-3" : "p-1")}>
          {user?.claims?.ADMIN && (
            <NavLink
              to="/admin"
              title={!expanded ? "Admin Panel" : undefined}
              className={({ isActive }) =>
                cn(
                  "flex items-center rounded transition-colors",
                  expanded ? "gap-2.5 px-2.5 py-1.5 text-sm" : "justify-center p-2",
                  isActive
                    ? "bg-primary/10 font-medium text-primary"
                    : "text-muted-foreground hover:bg-accent hover:text-foreground"
                )
              }
            >
              <Settings className="h-4 w-4 shrink-0" />
              {expanded && "Admin Panel"}
            </NavLink>
          )}
        </div>
      </aside>
    </>
  );
}
