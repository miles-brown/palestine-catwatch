import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { UserPlus, Eye, EyeOff, AlertCircle, CheckCircle, Info } from 'lucide-react';

// List of countries for the dropdown
const COUNTRIES = [
    "Afghanistan", "Albania", "Algeria", "Argentina", "Australia", "Austria",
    "Bangladesh", "Belgium", "Brazil", "Canada", "Chile", "China", "Colombia",
    "Czech Republic", "Denmark", "Egypt", "Finland", "France", "Germany", "Greece",
    "Hong Kong", "Hungary", "India", "Indonesia", "Iran", "Iraq", "Ireland",
    "Israel", "Italy", "Japan", "Jordan", "Kenya", "Kuwait", "Lebanon", "Malaysia",
    "Mexico", "Morocco", "Netherlands", "New Zealand", "Nigeria", "Norway",
    "Pakistan", "Palestine", "Peru", "Philippines", "Poland", "Portugal", "Qatar",
    "Romania", "Russia", "Saudi Arabia", "Singapore", "South Africa", "South Korea",
    "Spain", "Sweden", "Switzerland", "Syria", "Taiwan", "Thailand", "Turkey",
    "Ukraine", "United Arab Emirates", "United Kingdom", "United States", "Vietnam",
    "Yemen", "Other"
].sort();

export default function RegisterPage() {
    const navigate = useNavigate();
    const { register, isAuthenticated } = useAuth();

    const [step, setStep] = useState(1); // 1: form, 2: verification pending
    const [formData, setFormData] = useState({
        username: '',
        email: '',
        password: '',
        confirmPassword: '',
        full_name: '',
        date_of_birth: '',
        city: '',
        country: '',
        consent_given: false,
    });
    const [showPassword, setShowPassword] = useState(false);
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const [verificationToken, setVerificationToken] = useState(null);

    // Redirect if already authenticated
    if (isAuthenticated) {
        navigate('/', { replace: true });
        return null;
    }

    const handleChange = (e) => {
        const { name, value, type, checked } = e.target;
        setFormData(prev => ({
            ...prev,
            [name]: type === 'checkbox' ? checked : value
        }));
    };

    const validateForm = () => {
        if (formData.password !== formData.confirmPassword) {
            setError('Passwords do not match');
            return false;
        }

        if (formData.password.length < 8) {
            setError('Password must be at least 8 characters');
            return false;
        }

        // Check age (must be 18+)
        const dob = new Date(formData.date_of_birth);
        const today = new Date();
        let age = today.getFullYear() - dob.getFullYear();
        const monthDiff = today.getMonth() - dob.getMonth();
        if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < dob.getDate())) {
            age--;
        }
        if (age < 18) {
            setError('You must be at least 18 years old to create an account');
            return false;
        }

        if (!formData.consent_given) {
            setError('You must consent to the terms to create an account');
            return false;
        }

        return true;
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');

        if (!validateForm()) return;

        setLoading(true);

        const result = await register({
            username: formData.username,
            email: formData.email,
            password: formData.password,
            full_name: formData.full_name,
            date_of_birth: formData.date_of_birth,
            city: formData.city,
            country: formData.country,
            consent_given: formData.consent_given,
        });

        if (result.success) {
            setVerificationToken(result.verificationToken);
            setStep(2);
        } else {
            setError(result.error);
        }

        setLoading(false);
    };

    const handleVerify = async () => {
        if (!verificationToken) return;

        // In production, this would be done via email link
        // For dev, we can verify directly
        const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
        try {
            const response = await fetch(`${API_URL}/auth/verify-email/${verificationToken}`);
            if (response.ok) {
                navigate('/login?verified=true');
            } else {
                setError('Verification failed. Please try again.');
            }
        } catch (e) {
            setError('Verification failed. Please try again.');
        }
    };

    if (step === 2) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-900 via-slate-900 to-gray-900 p-4">
                <Card className="w-full max-w-md p-8 bg-slate-800 border-slate-700 shadow-2xl">
                    <div className="text-center mb-8">
                        <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-green-500/10 mb-4">
                            <CheckCircle className="h-8 w-8 text-green-500" />
                        </div>
                        <h1 className="text-2xl font-bold text-white mb-2">Verify Your Email</h1>
                        <p className="text-slate-400 text-sm">
                            We've sent a verification link to <strong>{formData.email}</strong>
                        </p>
                    </div>

                    <div className="space-y-4">
                        <div className="p-4 bg-slate-900 rounded-lg border border-slate-700">
                            <p className="text-slate-300 text-sm">
                                Please check your email and click the verification link to activate your account.
                            </p>
                        </div>

                        {/* Dev mode: direct verification button */}
                        {verificationToken && (
                            <div className="p-4 bg-yellow-500/10 rounded-lg border border-yellow-500/30">
                                <div className="flex items-start gap-2">
                                    <Info className="h-4 w-4 text-yellow-400 mt-0.5 flex-shrink-0" />
                                    <div>
                                        <p className="text-yellow-400 text-sm font-medium">Development Mode</p>
                                        <p className="text-yellow-400/70 text-xs mt-1">
                                            Click below to verify immediately (in production, use the email link)
                                        </p>
                                        <Button
                                            onClick={handleVerify}
                                            className="mt-3 bg-yellow-600 hover:bg-yellow-700 text-white text-sm"
                                            size="sm"
                                        >
                                            Verify Now (Dev Only)
                                        </Button>
                                    </div>
                                </div>
                            </div>
                        )}

                        <div className="text-center pt-4">
                            <Link to="/login" className="text-green-400 hover:text-green-300 text-sm">
                                Back to Login
                            </Link>
                        </div>
                    </div>
                </Card>
            </div>
        );
    }

    return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-900 via-slate-900 to-gray-900 p-4 py-8">
            <Card className="w-full max-w-lg p-8 bg-slate-800 border-slate-700 shadow-2xl">
                <div className="text-center mb-6">
                    <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-green-500/10 mb-3">
                        <UserPlus className="h-6 w-6 text-green-500" />
                    </div>
                    <h1 className="text-2xl font-bold text-white mb-1">Create Account</h1>
                    <p className="text-slate-400 text-sm">
                        Join the Palestine Accountability platform
                    </p>
                </div>

                <form onSubmit={handleSubmit} className="space-y-4">
                    {/* Account Information */}
                    <div className="space-y-3">
                        <h3 className="text-sm font-medium text-slate-300 border-b border-slate-700 pb-2">
                            Account Information
                        </h3>

                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <label htmlFor="username" className="block text-xs font-medium text-slate-400 mb-1">
                                    Username *
                                </label>
                                <input
                                    type="text"
                                    id="username"
                                    name="username"
                                    value={formData.username}
                                    onChange={handleChange}
                                    className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-white text-sm placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-green-500"
                                    required
                                />
                            </div>
                            <div>
                                <label htmlFor="email" className="block text-xs font-medium text-slate-400 mb-1">
                                    Email *
                                </label>
                                <input
                                    type="email"
                                    id="email"
                                    name="email"
                                    value={formData.email}
                                    onChange={handleChange}
                                    className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-white text-sm placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-green-500"
                                    required
                                />
                            </div>
                        </div>

                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <label htmlFor="password" className="block text-xs font-medium text-slate-400 mb-1">
                                    Password *
                                </label>
                                <div className="relative">
                                    <input
                                        type={showPassword ? 'text' : 'password'}
                                        id="password"
                                        name="password"
                                        value={formData.password}
                                        onChange={handleChange}
                                        className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-white text-sm placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-green-500"
                                        required
                                        minLength={8}
                                    />
                                    <button
                                        type="button"
                                        onClick={() => setShowPassword(!showPassword)}
                                        className="absolute right-2 top-1/2 transform -translate-y-1/2 text-slate-400 hover:text-slate-300"
                                    >
                                        {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                                    </button>
                                </div>
                            </div>
                            <div>
                                <label htmlFor="confirmPassword" className="block text-xs font-medium text-slate-400 mb-1">
                                    Confirm Password *
                                </label>
                                <input
                                    type={showPassword ? 'text' : 'password'}
                                    id="confirmPassword"
                                    name="confirmPassword"
                                    value={formData.confirmPassword}
                                    onChange={handleChange}
                                    className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-white text-sm placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-green-500"
                                    required
                                />
                            </div>
                        </div>
                    </div>

                    {/* Personal Information */}
                    <div className="space-y-3">
                        <h3 className="text-sm font-medium text-slate-300 border-b border-slate-700 pb-2">
                            Personal Information
                        </h3>

                        <div>
                            <label htmlFor="full_name" className="block text-xs font-medium text-slate-400 mb-1">
                                Full Name *
                            </label>
                            <input
                                type="text"
                                id="full_name"
                                name="full_name"
                                value={formData.full_name}
                                onChange={handleChange}
                                className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-white text-sm placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-green-500"
                                required
                            />
                        </div>

                        <div>
                            <label htmlFor="date_of_birth" className="block text-xs font-medium text-slate-400 mb-1">
                                Date of Birth * (must be 18+)
                            </label>
                            <input
                                type="date"
                                id="date_of_birth"
                                name="date_of_birth"
                                value={formData.date_of_birth}
                                onChange={handleChange}
                                max={new Date(new Date().setFullYear(new Date().getFullYear() - 18)).toISOString().split('T')[0]}
                                className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
                                required
                            />
                        </div>

                        <div className="grid grid-cols-2 gap-3">
                            <div>
                                <label htmlFor="city" className="block text-xs font-medium text-slate-400 mb-1">
                                    City *
                                </label>
                                <input
                                    type="text"
                                    id="city"
                                    name="city"
                                    value={formData.city}
                                    onChange={handleChange}
                                    className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-white text-sm placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-green-500"
                                    required
                                />
                            </div>
                            <div>
                                <label htmlFor="country" className="block text-xs font-medium text-slate-400 mb-1">
                                    Country *
                                </label>
                                <select
                                    id="country"
                                    name="country"
                                    value={formData.country}
                                    onChange={handleChange}
                                    className="w-full px-3 py-2 bg-slate-900 border border-slate-600 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-green-500"
                                    required
                                >
                                    <option value="">Select country</option>
                                    {COUNTRIES.map(country => (
                                        <option key={country} value={country}>{country}</option>
                                    ))}
                                </select>
                            </div>
                        </div>
                    </div>

                    {/* Consent */}
                    <div className="space-y-3">
                        <h3 className="text-sm font-medium text-slate-300 border-b border-slate-700 pb-2">
                            Terms & Consent
                        </h3>

                        <div className="p-3 bg-slate-900 rounded-lg border border-slate-700 text-xs text-slate-400 max-h-32 overflow-y-auto">
                            <p className="mb-2">By creating an account, you agree to the following:</p>
                            <ul className="list-disc list-inside space-y-1">
                                <li>Any images, videos, or information you upload may be stored and used by the Palestine Accountability Campaign.</li>
                                <li>You grant our non-profit organization full rights to use, modify, and distribute your contributions for accountability and documentation purposes.</li>
                                <li>Your personal information will be stored securely and used only for account management and communication.</li>
                                <li>You confirm that you are at least 18 years old and have the legal authority to agree to these terms.</li>
                                <li>You understand that this platform documents police activity and your contributions may be used in public reports.</li>
                            </ul>
                        </div>

                        <label className="flex items-start gap-3 cursor-pointer">
                            <input
                                type="checkbox"
                                name="consent_given"
                                checked={formData.consent_given}
                                onChange={handleChange}
                                className="mt-1 w-4 h-4 rounded border-slate-600 bg-slate-900 text-green-500 focus:ring-green-500"
                                required
                            />
                            <span className="text-sm text-slate-300">
                                I have read and agree to the terms above. I consent to the storage and use of my information and any media I upload for the purposes described. *
                            </span>
                        </label>
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
                        disabled={loading}
                    >
                        {loading ? 'Creating Account...' : 'Create Account'}
                    </Button>
                </form>

                <div className="mt-4 pt-4 border-t border-slate-700 text-center">
                    <p className="text-slate-400 text-sm">
                        Already have an account?{' '}
                        <Link to="/login" className="text-green-400 hover:text-green-300 font-medium">
                            Sign In
                        </Link>
                    </p>
                </div>
            </Card>
        </div>
    );
}
