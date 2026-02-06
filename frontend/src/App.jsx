import { useState, useEffect, lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import ErrorBoundary from './components/ErrorBoundary';
import { ToastProvider } from './components/Toast';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { SettingsProvider } from './contexts/SettingsContext';
import { BuildProvider } from './contexts/BuildContext';
import { PricingProvider } from './contexts/PricingContext';
import { initializeAuth } from './services/api';

// ... (Page imports stay the same)

// Protected route wrapper - requires authentication
const ProtectedRoute = ({ children }) => {
    const { user, loading } = useAuth();

    if (loading) return <FullPageLoader />;
    if (!user) return <Navigate to="/login" replace />;

    return children;
};

// Admin route wrapper - requires admin role
const AdminRoute = ({ children }) => {
    const { user, loading, isAdmin } = useAuth();

    if (loading) return <FullPageLoader />;
    if (!user) return <Navigate to="/login" replace />;
    if (!isAdmin) return <Navigate to="/" replace />;

    return children;
};

// Public route wrapper - redirects to dashboard if already authenticated
const PublicRoute = ({ children }) => {
    const { user, loading } = useAuth();

    if (loading) return <FullPageLoader />;
    if (user) return <Navigate to="/" replace />;

    return children;
};

function App() {
    const [authInitialized, setAuthInitialized] = useState(false);

    useEffect(() => {
        initializeAuth().finally(() => setAuthInitialized(true));
    }, []);

    if (!authInitialized) return <FullPageLoader />;

    return (
        <ErrorBoundary>
            <AuthProvider>
                <BuildProvider>
                    <SettingsProvider>
                        <PricingProvider>
                            <ToastProvider>
                                <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
                                    <Routes>
                                        <Route path="/login" element={<PublicRoute><Login /></PublicRoute>} />
                                        <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
                                            <Route index element={<LazyPage><Dashboard /></LazyPage>} />
                                            {/* ... rest of routes ... */}
                                    <Route index element={
                                        <LazyPage>
                                            <Dashboard />
                                        </LazyPage>
                                    } />
                                    <Route path="admin" element={
                                        <AdminRoute>
                                            <LazyPage>
                                                <AdminDashboard />
                                            </LazyPage>
                                        </AdminRoute>
                                    } />
                                    <Route path="projects" element={
                                        <LazyPage>
                                            <Projects />
                                        </LazyPage>
                                    } />
                                    <Route path="licenses" element={
                                        <LazyPage>
                                            <Licenses />
                                        </LazyPage>
                                    } />
                                    <Route path="webhooks" element={
                                        <LazyPage>
                                            <Webhooks />
                                        </LazyPage>
                                    } />
                                    <Route path="settings" element={
                                        <LazyPage>
                                            <Settings />
                                        </LazyPage>
                                    } />
                                    <Route path="build-settings" element={
                                        <LazyPage>
                                            <BuildSettings />
                                        </LazyPage>
                                    } />
                                    <Route path="pricing" element={
                                        <LazyPage>
                                            <Pricing />
                                        </LazyPage>
                                    } />
                                </Route>

                                {/* Catch all - redirect to home */}
                                <Route path="*" element={<Navigate to="/" replace />} />
                            </Routes>
                        </BrowserRouter>
                    </ToastProvider>
                </PricingProvider>
            </SettingsProvider>
        </BuildProvider>
    </AuthProvider>
</ErrorBoundary>
);
}

export default App;
