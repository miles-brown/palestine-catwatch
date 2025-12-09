import { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import config from '../config/environment';

const AuthContext = createContext(null);

const API_URL = config.apiUrl;
const TOKEN_KEY = 'catwatch_auth_token';
const REFRESH_TOKEN_KEY = 'catwatch_refresh_token';
const USER_KEY = 'catwatch_auth_user';
const TOKEN_EXPIRY_KEY = 'catwatch_token_expiry';
// NOTE: CSRF tokens are NOT stored in localStorage for security reasons
// They are kept in React state only, and the cookie handles persistence

// Refresh token 2 minutes before expiry to prevent unexpected logouts
const TOKEN_REFRESH_MARGIN_MS = 2 * 60 * 1000;

export function AuthProvider({ children }) {
    const [user, setUser] = useState(null);
    const [token, setToken] = useState(null);
    const [refreshToken, setRefreshToken] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [csrfToken, setCsrfToken] = useState(null);

    // Ref to store the refresh timer
    const refreshTimerRef = useRef(null);

    // Ref to track if initialization has run (prevents circular dependency issues)
    const isInitialized = useRef(false);

    // Fetch CSRF token for protected operations
    // SECURITY: Token is kept in React state only, NOT localStorage
    // The cookie provides persistence across page refreshes
    const fetchCsrfToken = useCallback(async () => {
        try {
            const response = await fetch(`${API_URL}/csrf/token`, {
                credentials: 'include', // Include cookies for CSRF
            });
            if (response.ok) {
                const data = await response.json();
                setCsrfToken(data.csrf_token);
                // Do NOT store in localStorage - that defeats CSRF protection
                return data.csrf_token;
            }
        } catch (e) {
            console.error('Failed to fetch CSRF token:', e);
        }
        return null;
    }, []);

    // Clear refresh timer
    const clearRefreshTimer = useCallback(() => {
        if (refreshTimerRef.current) {
            clearTimeout(refreshTimerRef.current);
            refreshTimerRef.current = null;
        }
    }, []);

    // Schedule token refresh before expiry
    const scheduleTokenRefresh = useCallback((expiresIn) => {
        clearRefreshTimer();

        // Calculate when to refresh (2 minutes before expiry)
        const refreshTime = (expiresIn * 1000) - TOKEN_REFRESH_MARGIN_MS;

        if (refreshTime > 0) {
            console.log(`Scheduling token refresh in ${Math.round(refreshTime / 1000)} seconds`);
            refreshTimerRef.current = setTimeout(() => {
                refreshAccessToken();
            }, refreshTime);
        }
    }, []);

    // Refresh the access token using the refresh token
    const refreshAccessToken = useCallback(async () => {
        const storedRefreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);

        if (!storedRefreshToken) {
            console.log('No refresh token available');
            return false;
        }

        try {
            const response = await fetch(`${API_URL}/auth/refresh`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ refresh_token: storedRefreshToken }),
            });

            if (!response.ok) {
                // Refresh token invalid/expired, force logout
                console.log('Refresh token invalid, logging out');
                logoutInternal();
                return false;
            }

            const data = await response.json();

            // Update access token
            localStorage.setItem(TOKEN_KEY, data.access_token);
            localStorage.setItem(TOKEN_EXPIRY_KEY, String(Date.now() + (data.expires_in * 1000)));
            setToken(data.access_token);

            // Schedule next refresh
            scheduleTokenRefresh(data.expires_in);

            console.log('Token refreshed successfully');
            return true;
        } catch (e) {
            console.error('Token refresh failed:', e);
            return false;
        }
    }, [scheduleTokenRefresh]);

    // Internal logout without triggering state updates that could cause loops
    const logoutInternal = useCallback(() => {
        clearRefreshTimer();
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(REFRESH_TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
        localStorage.removeItem(TOKEN_EXPIRY_KEY);
        setToken(null);
        setRefreshToken(null);
        setUser(null);
    }, [clearRefreshTimer]);

    // Check for existing auth on mount
    // Uses async IIFE to properly await token refresh before setting loading=false
    // Uses isInitialized ref to prevent re-running on dependency changes
    useEffect(() => {
        // Prevent re-initialization (guards against circular dependency issues)
        if (isInitialized.current) {
            return;
        }
        isInitialized.current = true;

        const initAuth = async () => {
            const storedToken = localStorage.getItem(TOKEN_KEY);
            const storedRefreshToken = localStorage.getItem(REFRESH_TOKEN_KEY);
            const storedUser = localStorage.getItem(USER_KEY);
            const storedExpiry = localStorage.getItem(TOKEN_EXPIRY_KEY);

            if (storedToken && storedUser) {
                try {
                    const parsedUser = JSON.parse(storedUser);
                    setToken(storedToken);
                    setRefreshToken(storedRefreshToken);
                    setUser(parsedUser);

                    // Check if token is expired or about to expire
                    const expiry = storedExpiry ? parseInt(storedExpiry, 10) : 0;
                    const now = Date.now();

                    if (expiry && expiry < now + TOKEN_REFRESH_MARGIN_MS) {
                        // Token expired or about to expire, await refresh before continuing
                        // This prevents race conditions where components render before refresh completes
                        const refreshed = await refreshAccessToken();
                        if (!refreshed) {
                            // Refresh failed, clear auth state
                            logoutInternal();
                        }
                    } else if (expiry) {
                        // Schedule refresh for later
                        const remainingTime = Math.floor((expiry - now) / 1000);
                        scheduleTokenRefresh(remainingTime);
                    } else {
                        // No expiry info, verify token is still valid
                        await verifyToken(storedToken);
                    }
                } catch (e) {
                    // Invalid stored data, clear it
                    logoutInternal();
                }
            }
            // Only set loading false after all async operations complete
            setLoading(false);
        };

        initAuth();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []); // Empty deps - initialization runs once only (uses isInitialized ref for safety)

    // Cleanup on unmount
    useEffect(() => {
        return () => clearRefreshTimer();
    }, [clearRefreshTimer]);

    const verifyToken = async (authToken) => {
        try {
            const response = await fetch(`${API_URL}/auth/me`, {
                headers: {
                    'Authorization': `Bearer ${authToken}`
                }
            });

            if (!response.ok) {
                // Token invalid, try to refresh
                const refreshed = await refreshAccessToken();
                if (!refreshed) {
                    logoutInternal();
                }
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
                // Handle specific error codes
                if (typeof data.detail === 'object' && data.detail.code) {
                    throw new Error(data.detail.message || data.detail.code);
                }
                throw new Error(data.detail || 'Login failed');
            }

            // Store auth data including refresh token
            localStorage.setItem(TOKEN_KEY, data.access_token);
            localStorage.setItem(USER_KEY, JSON.stringify(data.user));

            // Store refresh token if provided
            if (data.refresh_token) {
                localStorage.setItem(REFRESH_TOKEN_KEY, data.refresh_token);
                setRefreshToken(data.refresh_token);
            }

            // Store token expiry time
            if (data.expires_in) {
                const expiryTime = Date.now() + (data.expires_in * 1000);
                localStorage.setItem(TOKEN_EXPIRY_KEY, String(expiryTime));
                // Schedule automatic token refresh
                scheduleTokenRefresh(data.expires_in);
            }

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
            // Get CSRF token from state (NOT localStorage for security)
            // If not in state, fetch a fresh one from the server
            let currentCsrfToken = csrfToken;
            if (!currentCsrfToken) {
                currentCsrfToken = await fetchCsrfToken();
            }

            const headers = {
                'Content-Type': 'application/json',
            };

            // Add CSRF token if available
            if (currentCsrfToken) {
                headers['X-CSRF-Token'] = currentCsrfToken;
            }

            const response = await fetch(`${API_URL}/auth/register`, {
                method: 'POST',
                headers,
                credentials: 'include', // Include cookies for CSRF
                body: JSON.stringify(userData),
            });

            const data = await response.json();

            if (!response.ok) {
                // If CSRF validation failed, refresh token and retry once
                if (response.status === 403 && data.detail?.code === 'csrf_validation_failed') {
                    currentCsrfToken = await fetchCsrfToken();
                    if (currentCsrfToken) {
                        headers['X-CSRF-Token'] = currentCsrfToken;
                        const retryResponse = await fetch(`${API_URL}/auth/register`, {
                            method: 'POST',
                            headers,
                            credentials: 'include',
                            body: JSON.stringify(userData),
                        });
                        const retryData = await retryResponse.json();
                        if (!retryResponse.ok) {
                            throw new Error(retryData.detail || 'Registration failed');
                        }
                        return {
                            success: true,
                            message: retryData.message,
                            verificationRequired: retryData.verification_required,
                            verificationToken: retryData.verification_token
                        };
                    }
                }
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
        logoutInternal();
    }, [logoutInternal]);

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
        refreshToken,
        csrfToken,
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
        refreshAccessToken,  // Expose for manual refresh if needed
        fetchCsrfToken,      // For components that need fresh CSRF tokens
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
