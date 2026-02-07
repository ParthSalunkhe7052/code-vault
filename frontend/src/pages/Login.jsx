import { useState, useMemo, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Activity, ArrowRight, Loader2, Lock, Hexagon, Mail } from 'lucide-react';
import { useToast } from '../components/Toast';
import { useAuth } from '../contexts/AuthContext';

const Login = () => {
    const toast = useToast();
    const { login, register } = useAuth();
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [name, setName] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [isRegisterMode, setIsRegisterMode] = useState(false);
    const navigate = useNavigate();
    const location = useLocation();

    useEffect(() => {
        const pathWantsSignup = location.pathname === '/signup';
        const queryWantsSignup = new URLSearchParams(location.search).get('mode') === 'signup';
        const shouldRegister = pathWantsSignup || queryWantsSignup;

        setIsRegisterMode(shouldRegister);
        setError('');
    }, [location.pathname, location.search]);

    // Email validation regex
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    // Validate inputs
    const validation = useMemo(() => {
        const errors = [];

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

    const validateInputs = () => {
        if (!emailRegex.test(email)) {
            setError('Please enter a valid email address');
            toast.error('Invalid email format');
            return false;
        }

        if (password.length < 8) {
            setError('Password must be at least 8 characters');
            toast.error('Password too short');
            return false;
        }

        if (isRegisterMode && name.trim().length < 2) {
            setError('Name must be at least 2 characters');
            toast.error('Name too short');
            return false;
        }

        return true;
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError('');

        // Additional validation before API call
        if (!validateInputs()) {
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
        } catch (err) {
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
    };

    return (
        <div className="min-h-screen flex items-center justify-center relative overflow-hidden bg-background font-sans selection:bg-primary/30 selection:text-primary-light">
            {/* Background Effects */}
            <div className="fixed inset-0 bg-grid-pattern opacity-20 pointer-events-none" />
            <div className="absolute inset-0 bg-gradient-to-b from-transparent via-background/80 to-background pointer-events-none" />

            {/* Animated Orbs */}
            <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-primary/20 rounded-full blur-[120px] animate-pulse duration-[4s]"></div>
            <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] bg-secondary/20 rounded-full blur-[120px] animate-pulse duration-[5s] delay-1000"></div>

            <div className="w-full max-w-md z-10 p-4 relative">
                <div className="glass-card p-8 md:p-10 relative overflow-hidden group border-t border-white/10 shadow-2xl">

                    {/* Scanner Effect */}
                    <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-primary to-transparent opacity-50 animate-scan"></div>

                    <div className="flex flex-col items-center mb-10">
                        <div className="relative w-20 h-20 mb-6 flex items-center justify-center">
                            <div className="absolute inset-0 border border-primary/30 rounded-full animate-spin-slow"></div>
                            <div className="absolute inset-2 border border-secondary/30 rounded-full animate-spin-reverse-slower"></div>
                            <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-primary to-indigo-600 flex items-center justify-center text-white shadow-lg shadow-primary/30 z-10">
                                <Activity size={28} />
                            </div>
                        </div>

                        <h1 className="text-2xl font-bold text-center text-white tracking-widest uppercase mb-2">
                            CODEVAULT
                        </h1>
                        <p className="text-primary text-[10px] font-mono tracking-[0.3em] uppercase opacity-80">
                            {isRegisterMode ? 'Create New Account' : 'Secure Access Terminal'}
                        </p>
                    </div>

                    <form onSubmit={handleSubmit} className="flex flex-col gap-6">
                        {isRegisterMode && (
                            <div className="flex items-center gap-4 group/input">
                                <div className="text-slate-500 group-focus-within/input:text-primary transition-colors">
                                    <Activity size={20} />
                                </div>
                                <input
                                    type="text"
                                    value={name}
                                    onChange={(e) => setName(e.target.value)}
                                    className="input flex-1 w-auto bg-slate-900/50 border-white/10 focus:border-primary/50 focus:ring-1 focus:ring-primary/50 transition-all text-sm"
                                    placeholder="Full Name"
                                    required
                                />
                            </div>
                        )}

                        <div className="flex items-center gap-4 group/input">
                            <div className="text-slate-500 group-focus-within/input:text-primary transition-colors">
                                <Mail size={20} />
                            </div>
                            <input
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                className="input flex-1 w-auto bg-slate-900/50 border-white/10 focus:border-primary/50 focus:ring-1 focus:ring-primary/50 transition-all text-sm"
                                placeholder="Email Address"
                                required
                            />
                        </div>

                        <div className="flex items-center gap-4 group/input">
                            <div className="text-slate-500 group-focus-within/input:text-primary transition-colors">
                                <Lock size={20} />
                            </div>
                            <input
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                className="input flex-1 w-auto bg-slate-900/50 border-white/10 focus:border-primary/50 focus:ring-1 focus:ring-primary/50 transition-all font-mono tracking-wider placeholder:font-sans placeholder:tracking-normal text-sm"
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

                        {/* Validation feedback (real-time) */}
                        {!loading && !error && validation.errors.length > 0 && (
                            <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-amber-400 text-xs font-mono animate-fade-in">
                                <ul className="list-disc list-inside space-y-1">
                                    {validation.errors.map((err, idx) => (
                                        <li key={idx}>{err}</li>
                                    ))}
                                </ul>
                            </div>
                        )}

                        <div className="flex justify-center mt-2">
                            <button
                                type="submit"
                                disabled={validation.disabled}
                                className={`btn-primary px-8 py-3 text-sm tracking-widest uppercase group rounded-full shadow-lg shadow-primary/20 hover:shadow-primary/40 transition-all ${
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
                                className="text-xs text-slate-400 hover:text-primary transition-colors font-mono uppercase tracking-wider"
                            >
                                {isRegisterMode ? '<- Back to Login' : 'Create New Account ->'}
                            </button>

                            {!isRegisterMode && (
                                <div>
                                    <a
                                        href={`mailto:support@license-wrapper.com?subject=Password Reset Request&body=Please reset my password for: ${encodeURIComponent(email)}`}
                                        className="block text-[10px] text-slate-500 hover:text-primary/70 transition-colors font-mono"
                                    >
                                        Forgot Password?
                                    </a>
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                <div className="mt-8 text-center flex justify-center gap-4 opacity-30">
                    <Hexagon size={14} className="text-slate-600 animate-pulse" />
                    <Hexagon size={14} className="text-slate-600 animate-pulse delay-100" />
                    <Hexagon size={14} className="text-slate-600 animate-pulse delay-200" />
                </div>
            </div>
        </div>
    );
};

export default Login;
