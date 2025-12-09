import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

/**
 * ProtectedRoute - Wrapper component that requires authentication
 *
 * Usage:
 *   <Route path="/upload" element={<ProtectedRoute><UploadPage /></ProtectedRoute>} />
 *   <Route path="/admin" element={<ProtectedRoute requireAdmin><AdminPage /></ProtectedRoute>} />
 */
export default function ProtectedRoute({
    children,
    requireAdmin = false,
    requireContributor = false,
}) {
    const { isAuthenticated, isAdmin, isContributor, loading } = useAuth();
    const location = useLocation();

    // Show loading state while checking auth
    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50">
                <div className="text-center">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-600 mx-auto"></div>
                    <p className="mt-4 text-gray-600">Checking authentication...</p>
                </div>
            </div>
        );
    }

    // Redirect to login if not authenticated
    if (!isAuthenticated) {
        return <Navigate to="/login" state={{ from: location }} replace />;
    }

    // Check admin requirement
    if (requireAdmin && !isAdmin) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
                <div className="text-center max-w-md">
                    <div className="text-6xl mb-4">🔒</div>
                    <h1 className="text-2xl font-bold text-gray-900 mb-2">Admin Access Required</h1>
                    <p className="text-gray-600 mb-4">
                        This page requires administrator privileges. Please contact an administrator if you need access.
                    </p>
                    <a href="/" className="text-green-600 hover:text-green-700 font-medium">
                        Return to Home
                    </a>
                </div>
            </div>
        );
    }

    // Check contributor requirement
    if (requireContributor && !isContributor) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
                <div className="text-center max-w-md">
                    <div className="text-6xl mb-4">📝</div>
                    <h1 className="text-2xl font-bold text-gray-900 mb-2">Contributor Access Required</h1>
                    <p className="text-gray-600 mb-4">
                        This page requires contributor privileges. Your account may need to be upgraded.
                    </p>
                    <a href="/" className="text-green-600 hover:text-green-700 font-medium">
                        Return to Home
                    </a>
                </div>
            </div>
        );
    }

    return children;
}

/**
 * AdminRoute - Shorthand for ProtectedRoute with admin requirement
 */
export function AdminRoute({ children }) {
    return <ProtectedRoute requireAdmin>{children}</ProtectedRoute>;
}

/**
 * ContributorRoute - Shorthand for ProtectedRoute with contributor requirement
 */
export function ContributorRoute({ children }) {
    return <ProtectedRoute requireContributor>{children}</ProtectedRoute>;
}
