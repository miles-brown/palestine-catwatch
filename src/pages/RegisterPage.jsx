import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
    FormInput,
    PasswordInput,
    FormSelect,
    FormCheckbox,
    FormSection,
} from '@/components/ui/FormInput';
import { UserPlus, AlertCircle, CheckCircle, Info } from 'lucide-react';

// ============================================================================
// Constants
// ============================================================================

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

const INITIAL_FORM_STATE = {
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
    full_name: '',
    date_of_birth: '',
    city: '',
    country: '',
    consent_given: false,
};

// ============================================================================
// Sub-Components
// ============================================================================

/**
 * Email Verification Pending Screen
 */
function VerificationPending({ email, verificationToken, onVerify, error }) {
    return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-900 via-slate-900 to-gray-900 p-4">
            <Card className="w-full max-w-md p-8 bg-slate-800 border-slate-700 shadow-2xl">
                <div className="text-center mb-8">
                    <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-green-500/10 mb-4">
                        <CheckCircle className="h-8 w-8 text-green-500" />
                    </div>
                    <h1 className="text-2xl font-bold text-white mb-2">Verify Your Email</h1>
                    <p className="text-slate-400 text-sm">
                        We've sent a verification link to <strong>{email}</strong>
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
                        <DevVerificationPanel
                            onVerify={onVerify}
                            error={error}
                        />
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

/**
 * Development-only verification panel
 */
function DevVerificationPanel({ onVerify, error }) {
    return (
        <div className="p-4 bg-yellow-500/10 rounded-lg border border-yellow-500/30">
            <div className="flex items-start gap-2">
                <Info className="h-4 w-4 text-yellow-400 mt-0.5 flex-shrink-0" />
                <div>
                    <p className="text-yellow-400 text-sm font-medium">Development Mode</p>
                    <p className="text-yellow-400/70 text-xs mt-1">
                        Click below to verify immediately (in production, use the email link)
                    </p>
                    <Button
                        onClick={onVerify}
                        className="mt-3 bg-yellow-600 hover:bg-yellow-700 text-white text-sm"
                        size="sm"
                    >
                        Verify Now (Dev Only)
                    </Button>
                    {error && (
                        <p className="text-red-400 text-xs mt-2">{error}</p>
                    )}
                </div>
            </div>
        </div>
    );
}

/**
 * Error Alert Component
 */
function ErrorAlert({ message }) {
    if (!message) return null;

    return (
        <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
            <AlertCircle className="h-4 w-4 flex-shrink-0" />
            {message}
        </div>
    );
}

/**
 * Terms & Consent Section
 */
function ConsentSection({ consent_given, onChange }) {
    return (
        <FormSection title="Terms & Consent">
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

            <FormCheckbox
                name="consent_given"
                checked={consent_given}
                onChange={onChange}
                required
                label="I have read and agree to the terms above. I consent to the storage and use of my information and any media I upload for the purposes described. *"
            />
        </FormSection>
    );
}

// ============================================================================
// Validation Helpers
// ============================================================================

function validateForm(formData) {
    if (formData.password !== formData.confirmPassword) {
        return { valid: false, error: 'Passwords do not match' };
    }

    if (formData.password.length < 8) {
        return { valid: false, error: 'Password must be at least 8 characters' };
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
        return { valid: false, error: 'You must be at least 18 years old to create an account' };
    }

    if (!formData.consent_given) {
        return { valid: false, error: 'You must consent to the terms to create an account' };
    }

    return { valid: true, error: null };
}

function getMaxDateOfBirth() {
    const date = new Date();
    date.setFullYear(date.getFullYear() - 18);
    return date.toISOString().split('T')[0];
}

// ============================================================================
// Main Component
// ============================================================================

export default function RegisterPage() {
    const navigate = useNavigate();
    const { register, isAuthenticated } = useAuth();

    const [step, setStep] = useState(1); // 1: form, 2: verification pending
    const [formData, setFormData] = useState(INITIAL_FORM_STATE);
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

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');

        const validation = validateForm(formData);
        if (!validation.valid) {
            setError(validation.error);
            return;
        }

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

    // Step 2: Verification Pending
    if (step === 2) {
        return (
            <VerificationPending
                email={formData.email}
                verificationToken={verificationToken}
                onVerify={handleVerify}
                error={error}
            />
        );
    }

    // Step 1: Registration Form
    return (
        <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-gray-900 via-slate-900 to-gray-900 p-4 py-8">
            <Card className="w-full max-w-lg p-8 bg-slate-800 border-slate-700 shadow-2xl">
                {/* Header */}
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
                    {/* Account Information Section */}
                    <FormSection title="Account Information">
                        <div className="grid grid-cols-2 gap-3">
                            <FormInput
                                label="Username"
                                name="username"
                                value={formData.username}
                                onChange={handleChange}
                                required
                            />
                            <FormInput
                                label="Email"
                                name="email"
                                type="email"
                                value={formData.email}
                                onChange={handleChange}
                                required
                            />
                        </div>

                        <div className="grid grid-cols-2 gap-3">
                            <PasswordInput
                                label="Password"
                                name="password"
                                value={formData.password}
                                onChange={handleChange}
                                showPassword={showPassword}
                                onToggleShow={() => setShowPassword(!showPassword)}
                                required
                                minLength={8}
                            />
                            <PasswordInput
                                label="Confirm Password"
                                name="confirmPassword"
                                value={formData.confirmPassword}
                                onChange={handleChange}
                                showPassword={showPassword}
                                required
                            />
                        </div>
                    </FormSection>

                    {/* Personal Information Section */}
                    <FormSection title="Personal Information">
                        <FormInput
                            label="Full Name"
                            name="full_name"
                            value={formData.full_name}
                            onChange={handleChange}
                            required
                        />

                        <FormInput
                            label="Date of Birth (must be 18+)"
                            name="date_of_birth"
                            type="date"
                            value={formData.date_of_birth}
                            onChange={handleChange}
                            max={getMaxDateOfBirth()}
                            required
                        />

                        <div className="grid grid-cols-2 gap-3">
                            <FormInput
                                label="City"
                                name="city"
                                value={formData.city}
                                onChange={handleChange}
                                required
                            />
                            <FormSelect
                                label="Country"
                                name="country"
                                value={formData.country}
                                onChange={handleChange}
                                options={COUNTRIES}
                                placeholder="Select country"
                                required
                            />
                        </div>
                    </FormSection>

                    {/* Consent Section */}
                    <ConsentSection
                        consent_given={formData.consent_given}
                        onChange={handleChange}
                    />

                    {/* Error Display */}
                    <ErrorAlert message={error} />

                    {/* Submit Button */}
                    <Button
                        type="submit"
                        className="w-full bg-green-600 hover:bg-green-700 text-white py-3"
                        disabled={loading}
                    >
                        {loading ? 'Creating Account...' : 'Create Account'}
                    </Button>
                </form>

                {/* Login Link */}
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
