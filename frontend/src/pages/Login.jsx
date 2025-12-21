import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Activity, ArrowRight, Loader2, Lock, Hexagon, Mail } from 'lucide-react';
import { auth } from '../services/api';
import { useToast } from '../components/Toast';

const Login = () => {
    const toast = useToast();
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [name, setName] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [isRegisterMode, setIsRegisterMode] = useState(false);
    const navigate = useNavigate();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError('');

        try {
            if (isRegisterMode) {
                await auth.register(email, password, name);
                toast.success('Account created successfully!');
            } else {
                await auth.login(email, password);
                toast.success('Welcome back!');
            }
            navigate('/');
        } catch (err) {
            let errorMessage = 'An error occurred';

            if (err.response?.status === 401) {
                errorMessage = 'Invalid email or password';
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

                        <div className="flex justify-center mt-2">
                            <button
                                type="submit"
                                disabled={loading}
                                className="btn-primary px-8 py-3 text-sm tracking-widest uppercase group rounded-full shadow-lg shadow-primary/20 hover:shadow-primary/40 transition-all"
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
                                {isRegisterMode ? '← Back to Login' : 'Create New Account →'}
                            </button>

                            {!isRegisterMode && (
                                <div>
                                    <a
                                        href={`mailto:support@license-wrapper.com?subject=Password Reset Request&body=Please reset my password for: ${email}`}
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
