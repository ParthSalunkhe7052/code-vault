import React, { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react';
import { auth } from '../services/api';
import { User } from '../types/api';

interface AuthContextType {
    user: User | null;
    loading: boolean;
    isAuthenticated: boolean;
    isAdmin: boolean;
    sessionExpired: boolean;
    refreshUser: () => Promise<User | null>;
    logout: () => Promise<void>;
    login: (email: string, password: string) => Promise<User>;
    register: (email: string, password: string, name: string) => Promise<User>;
    acknowledgeSessionExpired: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [user, setUser] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);
    const [sessionExpired, setSessionExpired] = useState(false);

    const refreshUser = useCallback(async () => {
        try {
            const userData = await auth.getMe();
            // Ensure userData matches User interface
            setUser(userData as User);
            return userData as User;
        } catch (error) {
            console.error('[AuthContext] Failed to refresh user:', error);
            return null;
        }
    }, []);

    const logout = useCallback(async () => {
        try {
            await auth.logout();
        } catch (error) {
            console.error('[AuthContext] Logout cleanup failed:', error);
        } finally {
            // Always clear user state regardless of storage cleanup success
            setUser(null);
            setSessionExpired(false);
        }
    }, []);

    const login = useCallback(async (email: string, password: string) => {
        const userData = await auth.login(email, password);
        setUser(userData as User);
        setSessionExpired(false);
        return userData as User;
    }, []);

    const register = useCallback(async (email: string, password: string, name: string) => {
        const userData = await auth.register(email, password, name);
        setUser(userData as User);
        setSessionExpired(false);
        return userData as User;
    }, []);

    /**
     * Acknowledge session expiry -- clears the flag and user state.
     * Call this when the user clicks "Log in again" in the SessionExpiredModal.
     */
    const acknowledgeSessionExpired = useCallback(() => {
        setUser(null);
        setSessionExpired(false);
    }, []);

    // Listen for session-expired events dispatched by the API interceptor
    useEffect(() => {
        const handleSessionExpired = () => {
            setSessionExpired(true);
        };

        window.addEventListener('session-expired', handleSessionExpired);
        return () => window.removeEventListener('session-expired', handleSessionExpired);
    }, []);

    useEffect(() => {
        const initAuth = async () => {
            if (auth.isAuthenticated()) {
                await refreshUser();
            }
            setLoading(false);
        };
        initAuth();
    }, [refreshUser]);

    const isAuthenticated = !!user;
    const isAdmin = user?.role === 'admin';

    const value = useMemo(() => ({
        user,
        loading,
        isAuthenticated,
        isAdmin,
        sessionExpired,
        refreshUser,
        logout,
        login,
        register,
        acknowledgeSessionExpired
    }), [user, loading, isAuthenticated, isAdmin, sessionExpired, refreshUser, logout, login, register, acknowledgeSessionExpired]);

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};