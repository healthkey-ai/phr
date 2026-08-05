import { useState } from "react";
import { Outlet } from "react-router-dom";
import { Menu } from "lucide-react";
import AppSidebar from "./AppSidebar";
import AppHeader from "./AppHeader";
import HealthKeyLogo from "@/components/HealthKeyLogo";

export default function AppLayout() {
  const [desktopExpanded, setDesktopExpanded] = useState(true);
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="flex min-h-svh bg-muted">
      <AppSidebar
        expanded={desktopExpanded}
        onToggle={() => setDesktopExpanded((e) => !e)}
        mobileOpen={mobileOpen}
        onMobileClose={() => setMobileOpen(false)}
      />

      <div className="flex flex-1 flex-col">
        <AppHeader layout="app">
          <button
            onClick={() => setMobileOpen(true)}
            className="rounded p-1.5 text-muted-foreground hover:bg-accent lg:hidden"
          >
            <Menu className="h-5 w-5" />
          </button>
          <HealthKeyLogo className="shrink-0" />
        </AppHeader>

        <main className="flex-1 px-4 py-6 sm:px-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
