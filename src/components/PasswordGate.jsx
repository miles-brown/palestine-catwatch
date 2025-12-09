import { useState, useEffect } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Lock, Eye, EyeOff, AlertCircle } from 'lucide-react';

// Simple hash function for client-side password comparison
// This is NOT cryptographically secure - it's just to prevent casual access
const simpleHash = (str) => {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
        const char = str.charCodeAt(i);
        hash = ((hash << 5) - hash) + char;
        hash = hash & hash;
    }
    return hash.toString(36);
};

// Pre-computed hash of "BeKindRewind123"
const VALID_HASH = simpleHash("BeKindRewind123");
const AUTH_KEY = 'catwatch_upload_auth';
const AUTH_EXPIRY_KEY = 'catwatch_upload_auth_expiry';
const AUTH_DURATION = 24 * 60 * 60 * 1000; // 24 hours

export default function PasswordGate({ children }) {
    const [isAuthenticated, setIsAuthenticated] = useState(false);
    const [password, setPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [error, setError] = useState('');
    const [isChecking, setIsChecking] = useState(true);

    // Check for existing auth on mount
    useEffect(() => {
        const storedHash = localStorage.getItem(AUTH_KEY);
        const expiry = localStorage.getItem(AUTH_EXPIRY_KEY);

        if (storedHash && expiry) {
            const expiryTime = parseInt(expiry, 10);
            if (Date.now() < expiryTime && storedHash === VALID_HASH) {
                setIsAuthenticated(true);
            } else {
                // Clear expired auth
                localStorage.removeItem(AUTH_KEY);
                localStorage.removeItem(AUTH_EXPIRY_KEY);
            }
        }
        setIsChecking(false);
    }, []);

    const handleSubmit = (e) => {
        e.preventDefault();
        setError('');

        const inputHash = simpleHash(password);

        if (inputHash === VALID_HASH) {
            // Store auth with expiry
            localStorage.setItem(AUTH_KEY, inputHash);
            localStorage.setItem(AUTH_EXPIRY_KEY, (Date.now() + AUTH_DURATION).toString());
            setIsAuthenticated(true);
        } else {
            setError('Incorrect password. Access denied.');
            setPassword('');
        }
    };

    const handleLogout = () => {
        localStorage.removeItem(AUTH_KEY);
        localStorage.removeItem(AUTH_EXPIRY_KEY);
        setIsAuthenticated(false);
        setPassword('');
    };

    if (isChecking) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50">
                <div className="animate-pulse text-gray-500">Checking access...</div>
            </div>
        );
    }

    if (isAuthenticated) {
        return (
            <div className="relative">
                {/* Logout button - positioned in corner */}
                <div className="absolute top-4 right-4 z-50">
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={handleLogout}
                        className="text-gray-500 hover:text-gray-700 text-xs"
                    >
                        <Lock className="h-3 w-3 mr-1" />
                        Logout
                    </Button>
                </div>
                {children}
            </div>
        );
    }

    return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-900 via-slate-900 to-gray-900 p-4">
            <Card className="w-full max-w-md p-8 bg-slate-800 border-slate-700 shadow-2xl">
                <div className="text-center mb-8">
                    <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-green-500/10 mb-4">
                        <Lock className="h-8 w-8 text-green-500" />
                    </div>
                    <h1 className="text-2xl font-bold text-white mb-2">Access Required</h1>
                    <p className="text-slate-400 text-sm">
                        This area is restricted. Please enter the access code to continue.
                    </p>
                </div>

                <form onSubmit={handleSubmit} className="space-y-6">
                    <div>
                        <label htmlFor="password" className="block text-sm font-medium text-slate-300 mb-2">
                            Access Code
                        </label>
                        <div className="relative">
                            <input
                                type={showPassword ? 'text' : 'password'}
                                id="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                placeholder="Enter access code"
                                className="w-full px-4 py-3 bg-slate-900 border border-slate-600 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-green-500 focus:border-transparent"
                                autoFocus
                            />
                            <button
                                type="button"
                                onClick={() => setShowPassword(!showPassword)}
                                className="absolute right-3 top-1/2 transform -translate-y-1/2 text-slate-400 hover:text-slate-300"
                            >
                                {showPassword ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                            </button>
                        </div>
                    </div>

                    {error && (
                        <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
                            <AlertCircle className="h-4 w-4 flex-shrink-0" />
                            {error}
                        </div>
                    )}

                    <Button
                        type="submit"
                        className="w-full bg-green-600 hover:bg-green-700 text-white py-3"
                        disabled={!password}
                    >
                        Access Upload Portal
                    </Button>
                </form>

                <div className="mt-6 pt-6 border-t border-slate-700">
                    <p className="text-xs text-slate-500 text-center">
                        Palestine Accountability Campaign - Authorized Access Only
                    </p>
                </div>
            </Card>
        </div>
    );
}
