import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import AccessDenied, { AdminAccessDenied, ContributorAccessDenied } from './AccessDenied';

/**
 * Loading spinner component for auth checks
 */
function AuthLoading() {
    return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
            <div className="text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-600 mx-auto"></div>
                <p className="mt-4 text-gray-600">Checking authentication...</p>
            </div>
        </div>
    );
}

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
        return <AuthLoading />;
    }

    // Redirect to login if not authenticated
    if (!isAuthenticated) {
        return <Navigate to="/login" state={{ from: location }} replace />;
    }

    // Check admin requirement - use reusable AccessDenied component
    if (requireAdmin && !isAdmin) {
        return <AdminAccessDenied />;
    }

    // Check contributor requirement - use reusable AccessDenied component
    if (requireContributor && !isContributor) {
        return <ContributorAccessDenied />;
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
