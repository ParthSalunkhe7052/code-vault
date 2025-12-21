import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import { ToastProvider } from './components/Toast';
import { SettingsProvider } from './contexts/SettingsContext';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import AdminDashboard from './pages/AdminDashboard';
import Projects from './pages/Projects';
import Licenses from './pages/Licenses';
import Webhooks from './pages/Webhooks';
import Settings from './pages/Settings';
import BuildSettings from './pages/BuildSettings';
import Pricing from './pages/Pricing';
import Billing from './pages/Billing';
import { auth } from './services/api';

// Protected route wrapper
const ProtectedRoute = ({ children }) => {
    const isAuthenticated = auth.isAuthenticated();

    if (!isAuthenticated) {
        return <Navigate to="/login" replace />;
    }

    return children;
};

// Admin route wrapper - requires admin role
const AdminRoute = ({ children }) => {
    const isAuthenticated = auth.isAuthenticated();
    const user = auth.getUser();

    if (!isAuthenticated) {
        return <Navigate to="/login" replace />;
    }

    if (user?.role !== 'admin') {
        return <Navigate to="/" replace />;
    }

    return children;
};

// Public route wrapper (redirects to dashboard if already authenticated)
const PublicRoute = ({ children }) => {
    const isAuthenticated = auth.isAuthenticated();

    if (isAuthenticated) {
        return <Navigate to="/" replace />;
    }

    return children;
};

function App() {
    return (
        <SettingsProvider>
            <ToastProvider>
                <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
                    <Routes>
                        {/* Public Routes */}
                        <Route
                            path="/login"
                            element={
                                <PublicRoute>
                                    <Login />
                                </PublicRoute>
                            }
                        />

                        {/* Protected Routes */}
                        <Route
                            path="/"
                            element={
                                <ProtectedRoute>
                                    <Layout />
                                </ProtectedRoute>
                            }
                        >
                            <Route index element={<Dashboard />} />
                            <Route path="admin" element={
                                <AdminRoute>
                                    <AdminDashboard />
                                </AdminRoute>
                            } />
                            <Route path="projects" element={<Projects />} />
                            <Route path="licenses" element={<Licenses />} />
                            <Route path="webhooks" element={<Webhooks />} />
                            <Route path="settings" element={<Settings />} />
                            <Route path="build-settings" element={<BuildSettings />} />
                            <Route path="pricing" element={<Pricing />} />
                            <Route path="billing" element={<Billing />} />
                        </Route>

                        {/* Catch all - redirect to home */}
                        <Route path="*" element={<Navigate to="/" replace />} />
                    </Routes>
                </BrowserRouter>
            </ToastProvider>
        </SettingsProvider>
    );
}

export default App;

