import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { AuthProvider } from "@/contexts/AuthContext";
import Guard from "@/components/guards/Guard";
import AppLayout from "@/components/layout/AppLayout";
import AdminLayout from "@/components/layout/AdminLayout";
import LoginPage from "@/pages/auth/LoginPage";
import SignupPage from "@/pages/auth/SignupPage";
import DashboardPage from "@/pages/dashboard/DashboardPage";
import LabResultsPage from "@/pages/labs/LabResultsPage";
import LabResultDetailPage from "@/pages/labs/LabResultDetailPage";
import LabUploadsPage from "@/pages/labs/LabUploadsPage";
import PatientRecordPage from "@/pages/patient/PatientRecordPage";
import ProfilePage from "@/pages/profile/ProfilePage";
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
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            {/* Public */}
            <Route path="/login" element={<Guard allow={(u) => !u} redirectTo="/dashboard"><LoginPage /></Guard>} />
            <Route path="/signup" element={<Guard allow={(u) => !u} redirectTo="/dashboard"><SignupPage /></Guard>} />

            {/* Authenticated — sidebar layout */}
            <Route element={<Guard allow={(u) => !!u}><AppLayout /></Guard>}>
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/labs/results" element={<LabResultsPage />} />
              <Route path="/labs/results/:test" element={<LabResultDetailPage />} />
              <Route path="/labs/uploads" element={<LabUploadsPage />} />
              <Route path="/patient/record" element={<PatientRecordPage />} />
              <Route path="/profile" element={<ProfilePage />} />
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
    </QueryClientProvider>
  );
}
