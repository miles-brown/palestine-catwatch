import { Component } from 'react';
import { AlertTriangle, RefreshCw, Home } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';

/**
 * Error Boundary component to catch JavaScript errors in child components.
 * Prevents the entire app from crashing when a component throws an error.
 */
class ErrorBoundary extends Component {
    constructor(props) {
        super(props);
        this.state = {
            hasError: false,
            error: null,
            errorInfo: null
        };
    }

    static getDerivedStateFromError(error) {
        // Update state so the next render shows the fallback UI
        return { hasError: true };
    }

    componentDidCatch(error, errorInfo) {
        // Log error details
        console.error('ErrorBoundary caught an error:', error, errorInfo);
        this.setState({
            error: error,
            errorInfo: errorInfo
        });

        // In production, you might want to send this to an error tracking service
        // Example: logErrorToService(error, errorInfo);
    }

    handleRefresh = () => {
        window.location.reload();
    };

    handleGoHome = () => {
        window.location.href = '/';
    };

    handleRetry = () => {
        this.setState({ hasError: false, error: null, errorInfo: null });
    };

    render() {
        if (this.state.hasError) {
            // Custom fallback UI
            return (
                <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4">
                    <Card className="max-w-lg w-full p-8 text-center">
                        <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-red-100 mb-6">
                            <AlertTriangle className="h-8 w-8 text-red-600" />
                        </div>

                        <h1 className="text-2xl font-bold text-gray-900 mb-2">
                            Something went wrong
                        </h1>

                        <p className="text-gray-600 mb-6">
                            {this.props.fallbackMessage ||
                             "We're sorry, but something unexpected happened. Please try refreshing the page."}
                        </p>

                        {/* Show error details in development */}
                        {process.env.NODE_ENV === 'development' && this.state.error && (
                            <div className="mb-6 p-4 bg-gray-100 rounded-lg text-left overflow-auto max-h-48">
                                <p className="text-sm font-mono text-red-600 mb-2">
                                    {this.state.error.toString()}
                                </p>
                                {this.state.errorInfo && (
                                    <pre className="text-xs text-gray-600 whitespace-pre-wrap">
                                        {this.state.errorInfo.componentStack}
                                    </pre>
                                )}
                            </div>
                        )}

                        <div className="flex flex-col sm:flex-row gap-3 justify-center">
                            <Button
                                onClick={this.handleRetry}
                                variant="outline"
                                className="flex items-center gap-2"
                            >
                                <RefreshCw className="h-4 w-4" />
                                Try Again
                            </Button>

                            <Button
                                onClick={this.handleRefresh}
                                className="flex items-center gap-2 bg-green-600 hover:bg-green-700"
                            >
                                <RefreshCw className="h-4 w-4" />
                                Refresh Page
                            </Button>

                            <Button
                                onClick={this.handleGoHome}
                                variant="ghost"
                                className="flex items-center gap-2"
                            >
                                <Home className="h-4 w-4" />
                                Go Home
                            </Button>
                        </div>

                        <p className="text-xs text-gray-500 mt-6">
                            If the problem persists, please try clearing your browser cache or contact support.
                        </p>
                    </Card>
                </div>
            );
        }

        return this.props.children;
    }
}

export default ErrorBoundary;
