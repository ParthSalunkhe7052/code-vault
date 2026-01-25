import { useState, useEffect, lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import ErrorBoundary from './components/ErrorBoundary';
import { ToastProvider } from './components/Toast';
import { SettingsProvider } from './contexts/SettingsContext';
import { BuildProvider } from './contexts/BuildContext';
import { PricingProvider } from './contexts/PricingContext';
import { auth, initializeAuth } from './services/api';

// =============================================================================
// Code Splitting: Lazy load page components for better performance
// =============================================================================

// Login is eagerly loaded since it's often the first page users see
import Login from './pages/Login';

// Lazy load other pages - they will be loaded on demand
const Dashboard = lazy(() => import('./pages/Dashboard'));
const AdminDashboard = lazy(() => import('./pages/AdminDashboard'));
const Projects = lazy(() => import('./pages/Projects'));
const Licenses = lazy(() => import('./pages/Licenses'));
const Webhooks = lazy(() => import('./pages/Webhooks'));
const Settings = lazy(() => import('./pages/Settings'));
const BuildSettings = lazy(() => import('./pages/BuildSettings'));
const Pricing = lazy(() => import('./pages/Pricing'));
const Billing = lazy(() => import('./pages/Billing'));

// =============================================================================
// Loading Components
// =============================================================================

// Full page loading spinner (used during auth initialization)
const FullPageLoader = () => (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-cyan-500"></div>
            <div className="text-slate-400">Initializing...</div>
        </div>
    </div>
);

// Content loading spinner (used for lazy-loaded components)
const PageLoader = () => (
    <div className="flex items-center justify-center p-8">
        <div className="flex flex-col items-center gap-3">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-cyan-500"></div>
            <div className="text-slate-400 text-sm">Loading...</div>
        </div>
    </div>
);

// Suspense wrapper for lazy components
const LazyPage = ({ children }) => (
    <Suspense fallback={<PageLoader />}>
        {children}
    </Suspense>
);

// =============================================================================
// Route Guards
// =============================================================================

// Protected route wrapper - requires authentication
const ProtectedRoute = ({ children }) => {
    const isAuthenticated = auth.isAuthenticated();

    if (!isAuthenticated) {
        return <Navigate to="/login" replace />;
    }

    return children;
};

// Admin route wrapper - requires admin role
const AdminRoute = ({ children }) => {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const isAuthenticated = auth.isAuthenticated();

    useEffect(() => {
        async function loadUser() {
            try {
                if (isAuthenticated) {
                    const userData = await auth.getUser();
                    setUser(userData);
                }
            } catch (error) {
                console.error('Failed to load user:', error);
            } finally {
                setLoading(false);
            }
        }
        loadUser();
    }, [isAuthenticated]);

    if (!isAuthenticated) {
        return <Navigate to="/login" replace />;
    }

    if (loading) {
        return <PageLoader />;
    }

    if (user?.role !== 'admin') {
        return <Navigate to="/" replace />;
    }

    return children;
};

// Public route wrapper - redirects to dashboard if already authenticated
const PublicRoute = ({ children }) => {
    const isAuthenticated = auth.isAuthenticated();

    if (isAuthenticated) {
        return <Navigate to="/" replace />;
    }

    return children;
};

// =============================================================================
// Main App Component
// =============================================================================

function App() {
    const [authInitialized, setAuthInitialized] = useState(false);

    useEffect(() => {
        // Initialize auth from encrypted storage on app startup
        initializeAuth()
            .catch((error) => {
                console.error('Auth initialization failed:', error);
                // Could show a toast notification here
            })
            .finally(() => {
                setAuthInitialized(true);
            });
    }, []);

    // Show loading screen while initializing auth
    if (!authInitialized) {
        return <FullPageLoader />;
    }

    return (
        <ErrorBoundary>
            <BuildProvider>
                <SettingsProvider>
                    <PricingProvider>
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
                                    <Route path="billing" element={
                                        <LazyPage>
                                            <Billing />
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
    </ErrorBoundary>
    );
}

export default App;
