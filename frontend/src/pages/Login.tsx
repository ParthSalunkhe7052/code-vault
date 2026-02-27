import React, { useState, useMemo, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Activity, ArrowRight, Loader2, Lock, Hexagon, Mail, X } from 'lucide-react';
import { useToast } from '../components/Toast';
import { useAuth } from '../contexts/AuthContext';
import api from '../services/api';

// Email validation regex (module-level constant — no need to recreate per render)
const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

// ---------------------------------------------------------------------------
// ForgotPasswordModal — self-service password reset request
// ---------------------------------------------------------------------------
interface ForgotPasswordModalProps {
    onClose: () => void;
}

const ForgotPasswordModal: React.FC<ForgotPasswordModalProps> = ({ onClose }) => {
    const toast = useToast();
    const [email, setEmail] = useState('');
    const [loading, setLoading] = useState(false);
    const [sent, setSent] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!emailRegex.test(email)) {
            toast.error('Please enter a valid email address');
            return;
        }
        setLoading(true);
        try {
            await api.post('/auth/forgot-password', { email: email.trim() });
        } catch {
            // Swallow errors — always show success to avoid email enumeration
        } finally {
            setLoading(false);
            setSent(true);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
            <div className="glass-card w-full max-w-sm p-8 relative animate-scale-in">
                <button
                    onClick={onClose}
                    className="absolute top-4 right-4 text-cv-text-dim hover:text-cv-text transition-colors"
                    aria-label="Close"
                >
                    <X size={18} />
                </button>

                <h2 className="text-lg font-bold text-cv-text mb-2">Reset Password</h2>

                {sent ? (
                    <div className="space-y-4">
                        <p className="text-sm text-cv-text-muted">
                            If an account exists for <span className="text-cv-text font-medium">{email}</span>, a password reset link has been sent. Check your inbox.
                        </p>
                        <button onClick={onClose} className="btn-primary w-full">
                            Back to Login
                        </button>
                    </div>
                ) : (
                    <form onSubmit={handleSubmit} className="space-y-4">
                        <p className="text-sm text-cv-text-muted">
                            Enter your account email and we&apos;ll send a reset link.
                        </p>
                        <div className="flex items-center gap-3">
                            <Mail size={18} className="text-cv-text-muted shrink-0" />
                            <input
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                placeholder="your@email.com"
                                required
                                className="input flex-1 w-auto text-sm"
                                autoFocus
                            />
                        </div>
                        <button
                            type="submit"
                            disabled={loading}
                            className="btn-primary w-full flex items-center justify-center gap-2"
                        >
                            {loading ? <Loader2 size={16} className="animate-spin" /> : 'Send Reset Link'}
                        </button>
                    </form>
                )}
            </div>
        </div>
    );
};

// ---------------------------------------------------------------------------

const Login: React.FC = () => {
    const toast = useToast();
    const { login, register } = useAuth();
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [name, setName] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [isRegisterMode, setIsRegisterMode] = useState(false);
    const [showForgotPassword, setShowForgotPassword] = useState(false);
    // Track which fields the user has touched so we only show errors after interaction
    const [touched, setTouched] = useState({ email: false, password: false, name: false });
    const navigate = useNavigate();
    const location = useLocation();

    useEffect(() => {
        const pathWantsSignup = location.pathname === '/signup';
        const queryWantsSignup = new URLSearchParams(location.search).get('mode') === 'signup';
        const shouldRegister = pathWantsSignup || queryWantsSignup;

        setIsRegisterMode(shouldRegister);
        setError('');
    }, [location.pathname, location.search]);

    // Validate inputs — only compute, don't display until touched
    const validation = useMemo(() => {
        const errors: string[] = [];

        if (!email || !emailRegex.test(email)) {
            errors.push('Valid email is required');
        }

        if (!password || password.length < 8) {
            errors.push('Password must be at least 8 characters');
        }

        if (isRegisterMode && (!name || name.trim().length < 2)) {
            errors.push('Name must be at least 2 characters');
        }

        return {
            isValid: errors.length === 0,
            errors,
            disabled: errors.length > 0 || loading
        };
    }, [email, password, name, isRegisterMode, loading]);

    // Only show real-time hints for fields the user has already interacted with
    const visibleErrors = validation.errors.filter(err => {
        if (err.includes('email') && !touched.email) return false;
        if (err.includes('Password') && !touched.password) return false;
        if (err.includes('Name') && !touched.name) return false;
        return true;
    });

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError('');

        if (!validation.isValid) {
            const firstError = validation.errors[0] || 'Invalid input';
            setError(firstError);
            toast.error(firstError);
            setLoading(false);
            return;
        }

        try {
            if (isRegisterMode) {
                await register(email.trim(), password, name.trim());
                toast.success('Account created successfully!');
            } else {
                await login(email.trim(), password);
                toast.success('Welcome back!');
            }
            navigate('/');
        } catch (err: any) {
            let errorMessage = 'An error occurred';

            if (err.response?.status === 401) {
                errorMessage = 'Invalid email or password';
            } else if (err.response?.status === 409) {
                errorMessage = 'Email already registered';
            } else if (err.response?.data?.detail) {
                errorMessage = err.response.data.detail;
            } else if (isRegisterMode) {
                errorMessage = 'Registration failed. Email may already be in use.';
            }

            setError(errorMessage);
            toast.error(errorMessage);
            console.error('Login/Register error:', err.response?.data || err.message);
        } finally {
            setLoading(false);
        }
    };

    const toggleMode = () => {
        setIsRegisterMode(!isRegisterMode);
        setError('');
        setEmail('');
        setPassword('');
        setName('');
        setTouched({ email: false, password: false, name: false });
    };

    return (
        <>
            <div className="min-h-screen flex items-center justify-center relative overflow-hidden bg-cv-bg font-sans selection:bg-cv-primary/30 selection:text-cv-text">
                {/* Background Effects */}
                <div className="fixed inset-0 bg-grid-pattern opacity-20 pointer-events-none" />
                <div className="absolute inset-0 bg-gradient-to-b from-transparent via-cv-bg/80 to-cv-bg pointer-events-none" />

                {/* Animated Orbs */}
                <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-cv-primary/20 rounded-full blur-[120px] animate-pulse duration-[4s]"></div>
                <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] bg-cv-secondary/20 rounded-full blur-[120px] animate-pulse duration-[5s] delay-1000"></div>

                <div className="w-full max-w-md z-10 p-4 relative">
                    <div className="glass-card p-8 md:p-10 relative overflow-hidden group border-t border-white/10 shadow-2xl">

                        {/* Scanner Effect */}
                        <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-cv-primary to-transparent opacity-50 animate-scan"></div>

                        <div className="flex flex-col items-center mb-10">
                            <div className="relative w-20 h-20 mb-6 flex items-center justify-center">
                                <div className="absolute inset-0 border border-cv-primary/30 rounded-full animate-spin-slow"></div>
                                <div className="absolute inset-2 border border-cv-secondary/30 rounded-full animate-spin-reverse-slower"></div>
                                <div className="w-14 h-14 rounded-xl bg-cv-primary-gradient flex items-center justify-center text-white shadow-lg shadow-cv-primary/30 z-10">
                                    <Activity size={28} />
                                </div>
                            </div>

                            <h1 className="text-2xl font-bold text-center text-cv-text tracking-widest uppercase mb-2">
                                CODEVAULT
                            </h1>
                            <p className="text-cv-primary text-[10px] font-mono tracking-[0.3em] uppercase opacity-80">
                                {isRegisterMode ? 'Create New Account' : 'Secure Access Terminal'}
                            </p>
                        </div>

                        <form onSubmit={handleSubmit} className="flex flex-col gap-6">
                            {isRegisterMode && (
                                <div className="flex items-center gap-4 group/input">
                                    <div className="text-cv-text-muted group-focus-within/input:text-cv-primary transition-colors">
                                        <Activity size={20} />
                                    </div>
                                    <input
                                        type="text"
                                        value={name}
                                        onChange={(e) => setName(e.target.value)}
                                        onBlur={() => setTouched(prev => ({ ...prev, name: true }))}
                                        className="input flex-1 w-auto text-sm"
                                        placeholder="Full Name"
                                        required
                                    />
                                </div>
                            )}

                            <div className="flex items-center gap-4 group/input">
                                <div className="text-cv-text-muted group-focus-within/input:text-cv-primary transition-colors">
                                    <Mail size={20} />
                                </div>
                                <input
                                    type="email"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    onBlur={() => setTouched(prev => ({ ...prev, email: true }))}
                                    className="input flex-1 w-auto text-sm"
                                    placeholder="Email Address"
                                    required
                                />
                            </div>

                            <div className="flex items-center gap-4 group/input">
                                <div className="text-cv-text-muted group-focus-within/input:text-cv-primary transition-colors">
                                    <Lock size={20} />
                                </div>
                                <input
                                    type="password"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    onBlur={() => setTouched(prev => ({ ...prev, password: true }))}
                                    className="input flex-1 w-auto font-mono tracking-wider placeholder:font-sans placeholder:tracking-normal text-sm"
                                    placeholder="Password"
                                    required
                                />
                            </div>

                            {error && (
                                <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-xs font-mono flex items-center gap-2 animate-fade-in">
                                    <div className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse"></div>
                                    {error}
                                </div>
                            )}

                            {/* Validation feedback — only shown for touched fields, not on pristine form */}
                            {!loading && !error && visibleErrors.length > 0 && (
                                <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-400 text-xs font-mono animate-fade-in">
                                    <ul className="list-disc list-inside space-y-1">
                                        {visibleErrors.map((err, idx) => (
                                            <li key={idx}>{err}</li>
                                        ))}
                                    </ul>
                                </div>
                            )}

                            <div className="flex justify-center mt-2">
                                <button
                                    type="submit"
                                    disabled={validation.disabled}
                                    className={`btn-primary px-8 py-3 text-sm tracking-widest uppercase group rounded-full shadow-lg shadow-cv-primary/20 hover:shadow-cv-primary/40 transition-all flex items-center gap-2 ${
                                        validation.disabled && !loading ? 'opacity-50 cursor-not-allowed' : ''
                                    }`}
                                >
                                    {loading ? (
                                        <Loader2 className="animate-spin" size={18} />
                                    ) : (
                                        <>
                                            {isRegisterMode ? 'Create Account' : 'Initialize Session'}
                                            <ArrowRight size={16} className="group-hover:translate-x-1 transition-transform" />
                                        </>
                                    )}
                                </button>
                            </div>
                        </form>

                        <div className="mt-8 pt-6 border-t border-white/5">
                            <div className="text-center space-y-3">
                                <button
                                    onClick={toggleMode}
                                    className="text-xs text-cv-text-muted hover:text-cv-primary transition-colors font-mono uppercase tracking-wider"
                                >
                                    {isRegisterMode ? '<- Back to Login' : 'Create New Account ->'}
                                </button>

                                {!isRegisterMode && (
                                    <div>
                                        <button
                                            type="button"
                                            onClick={() => setShowForgotPassword(true)}
                                            className="text-[10px] text-cv-text-dim hover:text-cv-primary/70 transition-colors font-mono"
                                        >
                                            Forgot Password?
                                        </button>
                                    </div>
                                )}
                            </div>
                        </div>
                    </div>

                    <div className="mt-8 text-center flex justify-center gap-4 opacity-30">
                        <Hexagon size={14} className="text-cv-text-dim animate-pulse" />
                        <Hexagon size={14} className="text-cv-text-dim animate-pulse delay-100" />
                        <Hexagon size={14} className="text-cv-text-dim animate-pulse delay-200" />
                    </div>
                </div>
            </div>

            {showForgotPassword && (
                <ForgotPasswordModal onClose={() => setShowForgotPassword(false)} />
            )}
        </>
    );
};

export default Login;
