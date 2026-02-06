import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { auth } from '../services/api';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

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
        await auth.logout();
        setUser(null);
    }, []);

    const login = useCallback(async (email, password) => {
        const userData = await auth.login(email, password);
        setUser(userData);
        return userData;
    }, []);

    const register = useCallback(async (email, password, name) => {
        const userData = await auth.register(email, password, name);
        setUser(userData);
        return userData;
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

    const value = {
        user,
        loading,
        isAuthenticated: !!user,
        isAdmin: user?.role === 'admin',
        refreshUser,
        logout,
        login,
        register
    };

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
