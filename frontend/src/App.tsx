import type { ReactElement } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { AppLayout } from "./components/layout/AppLayout";
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

function ProtectedRoute({ children }: { children: ReactElement }) {
  const { isAuthenticated, isLoading } = useAuth();
  if (isLoading) return <FullScreenSpinner />;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return children;
}

function PublicOnlyRoute({ children }: { children: ReactElement }) {
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

const ONBOARDING_STEPS: { path: string; element: ReactElement }[] = [
  { path: "/onboarding", element: <Welcome /> },
  { path: "/onboarding/demographics", element: <Demographics /> },
  { path: "/onboarding/conditions", element: <Conditions /> },
  { path: "/onboarding/lifestyle", element: <Lifestyle /> },
  { path: "/onboarding/family", element: <Family /> },
  { path: "/onboarding/summary", element: <Summary /> },
];

export default function App() {
  return (
    <>
      <a href="#main" className="skip-link">Skip to content</a>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />

        {/* Auth */}
        <Route
          path="/signup"
          element={
            <PublicOnlyRoute>
              <SignUp />
            </PublicOnlyRoute>
          }
        />
        <Route
          path="/login"
          element={
            <PublicOnlyRoute>
              <SignIn />
            </PublicOnlyRoute>
          }
        />
        {/* Legacy paths from the previous portal */}
        <Route path="/auth/sign-in" element={<Navigate to="/login" replace />} />
        <Route path="/auth/sign-up" element={<Navigate to="/signup" replace />} />

        {/* Onboarding (full-screen, outside the portal shell) */}
        {ONBOARDING_STEPS.map(({ path, element }) => (
          <Route
            key={path}
            path={path}
            element={<ProtectedRoute>{element}</ProtectedRoute>}
          />
        ))}

        {/* Portal */}
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <AppLayout />
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
