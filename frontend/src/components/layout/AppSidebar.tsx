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
  BarChart3,
  ExternalLink,
  ChevronDown,
  Menu,
  Settings,
  SlidersHorizontal,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import SettingsDialog from "@/components/settings/SettingsDialog";
import { cn } from "@/lib/utils";

/**
 * A nav item points either at a route in this app (`to`) or at another site
 * (`href`), never both — the union is what stops an external destination being
 * handed to NavLink, which would treat it as a path and route to a 404.
 */
type NavItem = {
  label: string;
  icon: LucideIcon;
  disabled?: boolean;
} & ({ to: string; href?: never } | { href: string; to?: never });

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
      // EXACT's remote; enabled wherever it is configured, same rule as the
      // other federated items.
      {
        label: "Find Trials",
        to: "/trials",
        icon: Microscope,
        disabled: !import.meta.env.VITE_EXACT_REMOTE_URL,
      },
    ],
  },
  {
    label: "Sharing",
    items: [
      { label: "Share My Record", to: "/share", icon: Link2, disabled: true },
    ],
  },
  {
    // A different audience from everything above, which is why it is its own
    // group rather than another entry under My Health.
    label: "For researchers",
    items: [
      { label: "Analytics", href: "https://analytics.healthkey.ai", icon: BarChart3 },
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
          className="flex w-full items-center justify-between px-3 py-1.5 text-xs font-semibold uppercase tracking-wider text-sidebar-foreground/70 hover:text-sidebar-accent-foreground"
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
                  key={item.to ?? item.href}
                  aria-disabled="true"
                  title={iconOnly ? item.label : "Coming soon"}
                  className={cn(
                    "flex items-center rounded-control text-sidebar-foreground/50 cursor-not-allowed",
                    iconOnly ? "justify-center p-2" : "gap-2.5 px-2.5 py-1.5 text-sm"
                  )}
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  {!iconOnly && item.label}
                </span>
              );
            }
            if (item.href !== undefined) {
              return (
                <a
                  key={item.href}
                  href={item.href}
                  // Another site, so a new tab: leaving the portal mid-task
                  // would drop whatever the patient was doing. `noopener`
                  // keeps the opened page from reaching back via window.opener.
                  target="_blank"
                  rel="noopener noreferrer"
                  title={iconOnly ? item.label : undefined}
                  className={cn(
                    "flex items-center rounded-control transition-colors",
                    iconOnly ? "justify-center p-2" : "gap-2.5 px-2.5 py-1.5 text-sm",
                    "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                  )}
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  {!iconOnly && (
                    <>
                      <span className="flex-1">{item.label}</span>
                      <ExternalLink className="h-3.5 w-3.5 shrink-0 opacity-60" aria-hidden="true" />
                      <span className="sr-only">(opens in a new tab)</span>
                    </>
                  )}
                </a>
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
                    "flex items-center rounded-control transition-colors",
                    iconOnly ? "justify-center p-2" : "gap-2.5 px-2.5 py-1.5 text-sm",
                    isActive
                      ? "bg-sidebar-active/10 font-medium text-sidebar-active-foreground"
                      : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
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


/**
 * Sidebar footer. Extracted because the mobile overlay and the desktop rail
 * both render it — inlining it twice is how the two drifted apart before.
 */
function SidebarFooter({
  iconOnly,
  isAdmin,
  onOpenSettings,
}: {
  iconOnly: boolean;
  isAdmin: boolean;
  onOpenSettings: () => void;
}) {
  const itemClass = cn(
    "flex w-full items-center rounded-control transition-colors text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
    iconOnly ? "justify-center p-2" : "gap-2.5 px-2.5 py-1.5 text-sm",
  );

  return (
    <>
      <button
        onClick={onOpenSettings}
        title={iconOnly ? "Settings" : undefined}
        className={itemClass}
      >
        <SlidersHorizontal className="h-4 w-4 shrink-0" />
        {!iconOnly && "Settings"}
      </button>
      {isAdmin && (
        <NavLink
          to="/admin"
          title={iconOnly ? "Admin Panel" : undefined}
          className={({ isActive }) =>
            cn(
              "flex items-center rounded-control transition-colors",
              iconOnly ? "justify-center p-2" : "gap-2.5 px-2.5 py-1.5 text-sm",
              isActive
                ? "bg-sidebar-active/10 font-medium text-sidebar-active-foreground"
                : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
            )
          }
        >
          <Settings className="h-4 w-4 shrink-0" />
          {!iconOnly && "Admin Panel"}
        </NavLink>
      )}
    </>
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
  // Held here rather than in each aside: both variants are mounted at once
  // (one hidden by a media query), so per-variant state would give two
  // dialogs and a toggle that only works in whichever the user is not using.
  const [settingsOpen, setSettingsOpen] = useState(false);

  return (
    <>
      <SettingsDialog open={settingsOpen} onOpenChange={setSettingsOpen} />
      {/* Backdrop for mobile */}
      {mobileOpen && (
        <div className="fixed inset-0 z-30 bg-black/40 lg:hidden" onClick={onMobileClose} />
      )}

      {/* Mobile overlay sidebar — always full width */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground transition-transform duration-200 lg:hidden",
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex h-14 items-center border-b border-border px-4">
          <button onClick={onMobileClose} className="rounded-control p-1 text-sidebar-foreground hover:bg-sidebar-accent">
            <Menu className="h-5 w-5" />
          </button>
        </div>
        <div className="flex-1 space-y-4 overflow-y-auto py-3">
          {navGroups.map((group) => (
            <NavGroupSection key={group.label} group={group} iconOnly={false} />
          ))}
        </div>
        <div className="space-y-0.5 border-t border-sidebar-border p-3">
          <SidebarFooter
            iconOnly={false}
            isAdmin={!!user?.claims?.ADMIN}
            onOpenSettings={() => setSettingsOpen(true)}
          />
        </div>
      </aside>

      {/* Desktop sidebar — expands/collapses to icon-only. */}
      <aside
        className={cn(
          // max-lg:hidden (not bare `hidden`): federated remotes inject their
          // compiled Tailwind into our <head> after our stylesheet, and a
          // remote's `.hidden` rule outranks our `lg:flex` by document order,
          // permanently hiding the sidebar. Media-scoped variants can't collide.
          // sticky + h-svh so the footer stays on screen. Without it the aside
          // stretches to the document height, and on any page with content the
          // footer — Settings, Admin Panel — sits below the fold, reachable
          // only by scrolling to the very bottom of the page.
          "max-lg:hidden lg:flex sticky top-0 h-svh shrink-0 flex-col border-r border-sidebar-border bg-sidebar text-sidebar-foreground transition-all duration-200",
          expanded ? "w-64" : "w-14"
        )}
      >
        <div className={cn("flex h-14 items-center border-b border-sidebar-border", expanded ? "px-4" : "justify-center")}>
          <button onClick={onToggle} className="rounded-control p-1 text-sidebar-foreground hover:bg-sidebar-accent">
            <Menu className="h-5 w-5" />
          </button>
        </div>
        <div className={cn("flex-1 overflow-y-auto py-3", expanded ? "space-y-4" : "space-y-2")}>
          {navGroups.map((group) => (
            <NavGroupSection key={group.label} group={group} iconOnly={!expanded} />
          ))}
        </div>
        <div className={cn("space-y-0.5 border-t border-sidebar-border", expanded ? "p-3" : "p-1")}>
          <SidebarFooter
            iconOnly={!expanded}
            isAdmin={!!user?.claims?.ADMIN}
            onOpenSettings={() => setSettingsOpen(true)}
          />
        </div>
      </aside>
    </>
  );
}
