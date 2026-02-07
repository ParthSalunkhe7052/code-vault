import React, { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react';
import { auth } from '../services/api';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);
    const [sessionExpired, setSessionExpired] = useState(false);

    const refreshUser = useCallback(async () => {
        try {
            const userData = await auth.getMe();
            setUser(userData);
            return userData;
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

    const login = useCallback(async (email, password) => {
        const userData = await auth.login(email, password);
        setUser(userData);
        setSessionExpired(false);
        return userData;
    }, []);

    const register = useCallback(async (email, password, name) => {
        const userData = await auth.register(email, password, name);
        setUser(userData);
        setSessionExpired(false);
        return userData;
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
