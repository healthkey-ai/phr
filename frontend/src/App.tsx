import { Navigate, Route, Routes } from "react-router-dom";

import { useAuth } from "./contexts/AuthContext";
import { SignIn } from "./pages/auth/SignIn";
import { SignUp } from "./pages/auth/SignUp";
import { Home } from "./pages/dashboard/Home";
import { Profile } from "./pages/dashboard/Profile";
import { Records } from "./pages/dashboard/Records";
import { Share } from "./pages/dashboard/Share";
import { Conditions } from "./pages/onboarding/Conditions";
import { Demographics } from "./pages/onboarding/Demographics";
import { Family } from "./pages/onboarding/Family";
import { Lifestyle } from "./pages/onboarding/Lifestyle";
import { Summary } from "./pages/onboarding/Summary";
import { Welcome } from "./pages/onboarding/Welcome";
import { DashboardShell } from "./components/layout/DashboardShell";

function ProtectedRoute({ children }: { children: JSX.Element }) {
  const { isAuthenticated, isLoading } = useAuth();
  if (isLoading) return <FullScreenSpinner />;
  if (!isAuthenticated) return <Navigate to="/auth/sign-in" replace />;
  return children;
}

function PublicOnlyRoute({ children }: { children: JSX.Element }) {
  const { isAuthenticated, isLoading } = useAuth();
  if (isLoading) return <FullScreenSpinner />;
  if (isAuthenticated) return <Navigate to="/dashboard" replace />;
  return children;
}

function FullScreenSpinner() {
  return (
    <div className="flex min-h-screen items-center justify-center">
      <div
        className="h-8 w-8 animate-spin rounded-full border-4 border-muted border-t-brand-700"
        role="status"
        aria-label="Loading"
      />
    </div>
  );
}

export default function App() {
  return (
    <>
      <a href="#main" className="skip-link">Skip to content</a>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />

        {/* Auth */}
        <Route
          path="/auth/sign-up"
          element={
            <PublicOnlyRoute>
              <SignUp />
            </PublicOnlyRoute>
          }
        />
        <Route
          path="/auth/sign-in"
          element={
            <PublicOnlyRoute>
              <SignIn />
            </PublicOnlyRoute>
          }
        />

        {/* Onboarding */}
        <Route
          path="/onboarding"
          element={
            <ProtectedRoute>
              <Welcome />
            </ProtectedRoute>
          }
        />
        <Route
          path="/onboarding/demographics"
          element={
            <ProtectedRoute>
              <Demographics />
            </ProtectedRoute>
          }
        />
        <Route
          path="/onboarding/conditions"
          element={
            <ProtectedRoute>
              <Conditions />
            </ProtectedRoute>
          }
        />
        <Route
          path="/onboarding/lifestyle"
          element={
            <ProtectedRoute>
              <Lifestyle />
            </ProtectedRoute>
          }
        />
        <Route
          path="/onboarding/family"
          element={
            <ProtectedRoute>
              <Family />
            </ProtectedRoute>
          }
        />
        <Route
          path="/onboarding/summary"
          element={
            <ProtectedRoute>
              <Summary />
            </ProtectedRoute>
          }
        />

        {/* Dashboard */}
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <DashboardShell />
            </ProtectedRoute>
          }
        >
          <Route index element={<Home />} />
          <Route path="records" element={<Records />} />
          <Route path="share" element={<Share />} />
          <Route path="profile" element={<Profile />} />
        </Route>

        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </>
  );
}
