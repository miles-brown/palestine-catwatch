/**
 * AccessDenied - Reusable component for displaying insufficient permissions messages.
 *
 * This extracts the repeated "insufficient permissions" UI pattern used in ProtectedRoute
 * into a single, customizable component.
 */

import { Link } from 'react-router-dom';
import { ShieldX, Lock, UserX } from 'lucide-react';

const PRESETS = {
    admin: {
        icon: Lock,
        emoji: null,
        title: 'Admin Access Required',
        message: 'This page requires administrator privileges. Please contact an administrator if you need access.',
    },
    contributor: {
        icon: UserX,
        emoji: null,
        title: 'Contributor Access Required',
        message: 'This page requires contributor privileges. Your account may need to be upgraded.',
    },
    authenticated: {
        icon: ShieldX,
        emoji: null,
        title: 'Authentication Required',
        message: 'Please log in to access this page.',
        linkText: 'Go to Login',
        linkTo: '/login',
    },
    default: {
        icon: ShieldX,
        emoji: null,
        title: 'Access Denied',
        message: 'You do not have permission to view this page.',
    },
};

export default function AccessDenied({
    type = 'default',
    title,
    message,
    icon: CustomIcon,
    emoji,
    linkTo = '/',
    linkText = 'Return to Home',
    children,
}) {
    // Get preset values or use defaults
    const preset = PRESETS[type] || PRESETS.default;

    // Allow overrides
    const finalTitle = title || preset.title;
    const finalMessage = message || preset.message;
    const finalEmoji = emoji || preset.emoji;
    const Icon = CustomIcon || preset.icon;
    const finalLinkTo = linkTo || preset.linkTo || '/';
    const finalLinkText = linkText || preset.linkText || 'Return to Home';

    return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
            <div className="text-center max-w-md">
                {/* Icon or Emoji */}
                {finalEmoji ? (
                    <div className="text-6xl mb-4">{finalEmoji}</div>
                ) : Icon ? (
                    <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-red-100 mb-4">
                        <Icon className="h-8 w-8 text-red-600" />
                    </div>
                ) : null}

                {/* Title */}
                <h1 className="text-2xl font-bold text-gray-900 mb-2">
                    {finalTitle}
                </h1>

                {/* Message */}
                <p className="text-gray-600 mb-4">
                    {finalMessage}
                </p>

                {/* Custom content */}
                {children}

                {/* Link back */}
                <Link
                    to={finalLinkTo}
                    className="text-green-600 hover:text-green-700 font-medium inline-block mt-2"
                >
                    {finalLinkText}
                </Link>
            </div>
        </div>
    );
}

/**
 * Preset components for common access denial scenarios
 */
export function AdminAccessDenied(props) {
    return <AccessDenied type="admin" {...props} />;
}

export function ContributorAccessDenied(props) {
    return <AccessDenied type="contributor" {...props} />;
}

export function AuthenticationRequired(props) {
    return <AccessDenied type="authenticated" {...props} />;
}
