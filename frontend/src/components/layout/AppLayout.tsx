/**
 * AppLayout — portal shell: sidebar + header + routed content.
 * Modeled on the ht-phr host app layout (sidebar/header/Outlet).
 */
import { useState } from "react";
import { Outlet } from "react-router-dom";

import { AppHeader } from "./AppHeader";
import { AppSidebar } from "./AppSidebar";

export function AppLayout() {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <div className="flex min-h-screen bg-healthkey-bg-secondary">
      <AppSidebar mobileOpen={mobileOpen} onClose={() => setMobileOpen(false)} />

      <div className="flex min-w-0 flex-1 flex-col">
        <AppHeader onOpenMenu={() => setMobileOpen(true)} />
        <main id="main" className="flex-1 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
