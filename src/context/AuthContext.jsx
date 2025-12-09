import { createContext, useContext, useState, useEffect, useCallback } from 'react';

const AuthContext = createContext(null);

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const TOKEN_KEY = 'catwatch_auth_token';
const USER_KEY = 'catwatch_auth_user';

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null);
    const [token, setToken] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // Check for existing auth on mount
    useEffect(() => {
        const storedToken = localStorage.getItem(TOKEN_KEY);
        const storedUser = localStorage.getItem(USER_KEY);

        if (storedToken && storedUser) {
            try {
                const parsedUser = JSON.parse(storedUser);
                setToken(storedToken);
                setUser(parsedUser);
                // Verify token is still valid
                verifyToken(storedToken);
            } catch (e) {
                // Invalid stored data, clear it
                localStorage.removeItem(TOKEN_KEY);
                localStorage.removeItem(USER_KEY);
            }
        }
        setLoading(false);
    }, []);

    const verifyToken = async (authToken) => {
        try {
            const response = await fetch(`${API_URL}/auth/me`, {
                headers: {
                    'Authorization': `Bearer ${authToken}`
                }
            });

            if (!response.ok) {
                // Token invalid, logout
                logout();
            }
        } catch (e) {
            console.error('Token verification failed:', e);
        }
    };

    const login = async (username, password) => {
        setError(null);
        try {
            const response = await fetch(`${API_URL}/auth/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ username, password }),
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Login failed');
            }

            // Store auth data
            localStorage.setItem(TOKEN_KEY, data.access_token);
            localStorage.setItem(USER_KEY, JSON.stringify(data.user));
            setToken(data.access_token);
            setUser(data.user);

            return { success: true, user: data.user };
        } catch (e) {
            setError(e.message);
            return { success: false, error: e.message };
        }
    };

    const register = async (userData) => {
        setError(null);
        try {
            const response = await fetch(`${API_URL}/auth/register`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(userData),
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Registration failed');
            }

            return {
                success: true,
                message: data.message,
                verificationRequired: data.verification_required,
                verificationToken: data.verification_token // For dev/testing
            };
        } catch (e) {
            setError(e.message);
            return { success: false, error: e.message };
        }
    };

    const verifyEmail = async (token) => {
        try {
            const response = await fetch(`${API_URL}/auth/verify-email/${token}`);
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Verification failed');
            }

            return { success: true, message: data.message };
        } catch (e) {
            return { success: false, error: e.message };
        }
    };

    const logout = useCallback(() => {
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
        setToken(null);
        setUser(null);
    }, []);

    const isAuthenticated = !!token && !!user;
    const isAdmin = user?.role === 'admin';
    const isContributor = user?.role === 'contributor' || user?.role === 'admin';

    const getAuthHeaders = useCallback(() => {
        if (!token) return {};
        return {
            'Authorization': `Bearer ${token}`
        };
    }, [token]);

    const value = {
        user,
        token,
        loading,
        error,
        isAuthenticated,
        isAdmin,
        isContributor,
        login,
        register,
        verifyEmail,
        logout,
        getAuthHeaders,
    };

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
}

export default AuthContext;
