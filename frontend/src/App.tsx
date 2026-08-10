import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "@/contexts/AuthContext";
import { BrandProvider } from "@/contexts/BrandContext";
import Guard from "@/components/guards/Guard";
import AppLayout from "@/components/layout/AppLayout";
import AdminLayout from "@/components/layout/AdminLayout";
import LoginPage from "@/pages/auth/LoginPage";
import SignupPage from "@/pages/auth/SignupPage";
import DashboardPage from "@/pages/dashboard/DashboardPage";
import LabResultsPage from "@/pages/labs/LabResultsPage";
import FindTreatmentsPage from "@/pages/treatments/FindTreatmentsPage";
import FindTrialsPage from "@/pages/trials/FindTrialsPage";
import LabResultDetailPage from "@/pages/labs/LabResultDetailPage";
import LabUploadsPage from "@/pages/labs/LabUploadsPage";
import PatientRecordPage from "@/pages/patient/PatientRecordPage";
import AdminDashboardPage from "@/pages/admin/AdminDashboardPage";
import RolesPage from "@/pages/admin/RolesPage";

const queryClient = new QueryClient();

const adminNavItems = [
  { label: "Dashboard", to: "/admin" },
  { label: "Roles", to: "/admin/roles" },
];

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrandProvider>
        <AuthProvider>
          <BrowserRouter>
            <Routes>
              {/* Public */}
              <Route path="/login" element={<Guard allow={(u) => !u} redirectTo="/dashboard"><LoginPage /></Guard>} />
              <Route path="/signup" element={<Guard allow={(u) => !u} redirectTo="/dashboard"><SignupPage /></Guard>} />

              {/* Authenticated — sidebar layout */}
              <Route element={<Guard allow={(u) => !!u}><AppLayout /></Guard>}>
                <Route path="/dashboard" element={<DashboardPage />} />
                {/* Labs routes stay registered while their menu items are
                    disabled: deep links keep working during the hk-labs
                    transition and degrade to the remote-unavailable card. */}
                <Route path="/treatments" element={<FindTreatmentsPage />} />
                <Route path="/trials" element={<FindTrialsPage />} />
                <Route path="/labs/results" element={<LabResultsPage />} />
                <Route path="/labs/results/:test" element={<LabResultDetailPage />} />
                <Route path="/labs/uploads" element={<LabUploadsPage />} />
                <Route path="/patient/record" element={<PatientRecordPage />} />
                {/* The local profile page was replaced by the federated Health
                    Profile (promop PatientInfo) at /patient/record. */}
                <Route path="/profile" element={<Navigate to="/patient/record" replace />} />
              </Route>

              {/* Admin (requires ADMIN role) */}
              <Route
                path="/admin"
                element={
                  <Guard allow={(u) => !!u?.claims?.ADMIN} redirectTo="/dashboard">
                    <AdminLayout title="Admin" navItems={adminNavItems} />
                  </Guard>
                }
              >
                <Route index element={<AdminDashboardPage />} />
                <Route path="roles" element={<RolesPage />} />
              </Route>

              <Route path="*" element={<Navigate to="/dashboard" replace />} />
            </Routes>
          </BrowserRouter>
        </AuthProvider>
      </BrandProvider>
    </QueryClientProvider>
  );
}
