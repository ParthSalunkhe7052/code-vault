import { useState, useEffect, lazy, Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import Layout from './components/Layout';
import ErrorBoundary from './components/ErrorBoundary';
import { ToastProvider } from './components/Toast';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { SettingsProvider } from './contexts/SettingsContext';
import { BuildProvider } from './contexts/BuildContext';
import { PricingProvider } from './contexts/PricingContext';
import { initializeAuth } from './services/api';
import Spinner from './components/Spinner';
import { AnimatedPage, pageVariants, pageTransition } from './components/AnimatedPage';
import SessionExpiredModal from './components/SessionExpiredModal';

// Lazy-loaded page components
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Login = lazy(() => import('./pages/Login'));
const Projects = lazy(() => import('./pages/Projects'));
const Licenses = lazy(() => import('./pages/Licenses'));
const Webhooks = lazy(() => import('./pages/Webhooks'));
const Settings = lazy(() => import('./pages/Settings'));
const BuildSettings = lazy(() => import('./pages/BuildSettings'));
const Pricing = lazy(() => import('./pages/Pricing'));
const AdminDashboard = lazy(() => import('./pages/AdminDashboard'));

// Renders SessionExpiredModal inside BrowserRouter so useNavigate is available
const SessionExpiredHandler = () => {
    const { sessionExpired, acknowledgeSessionExpired } = useAuth();
    const navigate = useNavigate();

    if (!sessionExpired) return null;

    return (
        <SessionExpiredModal
            onAcknowledge={() => {
                acknowledgeSessionExpired();
                navigate('/login');
            }}
        />
    );
};

// Full page loading spinner
const FullPageLoader = () => (
    <div className="min-h-screen flex items-center justify-center" style={{ backgroundColor: 'var(--cv-bg, #0a0a0f)' }}>
        <div className="flex flex-col items-center gap-4">
            <Spinner size="xl" />
            <p className="text-slate-400 text-sm animate-pulse">Loading...</p>
        </div>
    </div>
);

// Suspense wrapper for lazy-loaded pages with animation
const LazyPage = ({ children }) => (
    <Suspense fallback={
        <div className="flex items-center justify-center h-full min-h-[400px]">
            <Spinner size="lg" />
        </div>
    }>
        <AnimatedPage className="h-full" variants={pageVariants} transition={pageTransition}>
            {children}
        </AnimatedPage>
    </Suspense>
);

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
                                        <Route path="/login" element={
                                            <PublicRoute>
                                                <LazyPage><Login /></LazyPage>
                                            </PublicRoute>
                                        } />
                                        <Route path="/signup" element={
                                            <PublicRoute>
                                                <LazyPage><Login /></LazyPage>
                                            </PublicRoute>
                                        } />

                                        <Route path="/" element={
                                            <ProtectedRoute><Layout /></ProtectedRoute>
                                        }>
                                            <Route index element={
                                                <LazyPage><Dashboard /></LazyPage>
                                            } />
                                            <Route path="admin" element={
                                                <AdminRoute>
                                                    <LazyPage><AdminDashboard /></LazyPage>
                                                </AdminRoute>
                                            } />
                                            <Route path="projects" element={
                                                <LazyPage><Projects /></LazyPage>
                                            } />
                                            <Route path="licenses" element={
                                                <LazyPage><Licenses /></LazyPage>
                                            } />
                                            <Route path="webhooks" element={
                                                <LazyPage><Webhooks /></LazyPage>
                                            } />
                                            <Route path="settings" element={
                                                <LazyPage><Settings /></LazyPage>
                                            } />
                                            <Route path="build-settings" element={
                                                <LazyPage><BuildSettings /></LazyPage>
                                            } />
                                            <Route path="pricing" element={
                                                <LazyPage><Pricing /></LazyPage>
                                            } />
                                        </Route>

                                        {/* Legal pages - redirect to landing page */}
                                        <Route path="/privacy" element={<Navigate to="https://codevault.com/privacy" replace />} />
                                        <Route path="/terms" element={<Navigate to="https://codevault.com/terms" replace />} />
                                        <Route path="/gdpr" element={<Navigate to="https://codevault.com/gdpr" replace />} />
                                        <Route path="/sla" element={<Navigate to="https://codevault.com/sla" replace />} />

                                        {/* Catch all - redirect to home */}
                                        <Route path="*" element={<Navigate to="/" replace />} />
                                    </Routes>
                                    <SessionExpiredHandler />
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
