import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route, useNavigate } from 'react-router-dom';

// Import common components
import Navbar from './components/common/Navbar';
import Footer from './components/common/Footer';
import AlertPopup from './components/common/AlertPopup';

// Import page components
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import SimulationPage from './pages/SimulationPage';
import SettingsPage from './pages/SettingsPage';

// Import custom hooks
import { useAuth } from './hooks/useAuth';

/**
 * A wrapper component that checks authentication status via the useAuth hook
 * and redirects unauthenticated users to the login page.
 * @param {{ children: React.ReactNode }} props The component props.
 * @returns {React.ReactElement | null} The protected content, a loading indicator, or null while redirecting.
 */
const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    // If the authentication check is complete and the user is not authenticated,
    // redirect to the login page.
    if (!loading && !isAuthenticated) {
      navigate('/login');
    }
  }, [isAuthenticated, loading, navigate]);

  // While checking authentication, display a loading message.
  if (loading) {
    return <div className="text-center p-8">Loading authentication...</div>;
  }

  // If authenticated, render the child components.
  if (isAuthenticated) {
    return children;
  }

  // If not authenticated and not loading, the redirect is in progress.
  // Return null to avoid rendering anything before the redirect happens.
  return null;
};

/**
 * The root component of the application that sets up the main layout and routing.
 */
function App() {
  return (
    <BrowserRouter>
      <div className="flex flex-col min-h-screen bg-gray-100">
        <Navbar />
        <main className="flex-grow container mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <AlertPopup />
          <Routes>
            {/* Public Route */}
            <Route path="/login" element={<LoginPage />} />

            {/* Protected Routes */}
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <DashboardPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/simulation"
              element={
                <ProtectedRoute>
                  <SimulationPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/settings"
              element={
                <ProtectedRoute>
                  <SettingsPage />
                </ProtectedRoute>
              }
            />
          </Routes>
        </main>
        <Footer />
      </div>
    </BrowserRouter>
  );
}

export default App;
