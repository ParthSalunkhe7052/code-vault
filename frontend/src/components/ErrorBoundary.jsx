import React from 'react';
import { AlertTriangle, RefreshCw, Home } from 'lucide-react';

/**
 * Error Boundary Component
 * Catches JavaScript errors anywhere in the child component tree,
 * logs those errors, and displays a fallback UI.
 */
class ErrorBoundary extends React.Component {
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
        this.setState({ error, errorInfo });

        // Log to console in development
        console.error('ErrorBoundary caught an error:', error, errorInfo);

        // In production, you could send to an error reporting service here
        // e.g., Sentry, LogRocket, etc.
    }

    handleReset = () => {
        this.setState({
            hasError: false,
            error: null,
            errorInfo: null
        });
    };

    handleGoHome = () => {
        this.handleReset();
        window.location.href = '/';
    };

    render() {
        if (this.state.hasError) {
            return (
                <div className="min-h-screen flex items-center justify-center bg-background p-4">
                    <div className="glass-card p-8 max-w-lg w-full text-center">
                        {/* Error Icon */}
                        <div className="w-20 h-20 mx-auto mb-6 rounded-full bg-red-500/10 flex items-center justify-center">
                            <AlertTriangle size={40} className="text-red-400" />
                        </div>

                        {/* Error Message */}
                        <h1 className="text-2xl font-bold text-white mb-3">
                            Something went wrong
                        </h1>
                        <p className="text-slate-400 mb-6">
                            An unexpected error occurred. Don't worry, your data is safe.
                            Please try refreshing the page or go back to the dashboard.
                        </p>

                        {/* Action Buttons */}
                        <div className="flex gap-3 justify-center mb-6">
                            <button
                                onClick={this.handleReset}
                                className="btn btn-secondary flex items-center gap-2"
                            >
                                Try Again
                            </button>
                            <button
                                onClick={() => window.location.reload()}
                                className="btn btn-primary flex items-center gap-2"
                            >
                                <RefreshCw size={16} />
                                Refresh Page
                            </button>
                        </div>

                        <button
                            onClick={this.handleGoHome}
                            className="text-slate-400 hover:text-white text-sm flex items-center gap-2 mx-auto transition-colors"
                        >
                            <Home size={14} />
                            Go to Dashboard
                        </button>

                        {/* Error Details (Development Only) */}
                        {import.meta.env.DEV && this.state.error && (
                            <details className="mt-8 text-left">
                                <summary className="text-sm text-slate-500 cursor-pointer hover:text-slate-400 transition-colors">
                                    Show Error Details (Development Only)
                                </summary>
                                <div className="mt-3 p-4 bg-slate-800/50 rounded-lg overflow-auto max-h-64 custom-scrollbar">
                                    <p className="text-red-400 text-sm font-mono mb-2">
                                        {this.state.error.toString()}
                                    </p>
                                    {this.state.errorInfo?.componentStack && (
                                        <pre className="text-xs text-slate-500 whitespace-pre-wrap">
                                            {this.state.errorInfo.componentStack}
                                        </pre>
                                    )}
                                </div>
                            </details>
                        )}
                    </div>
                </div>
            );
        }

        return this.props.children;
    }
}

export default ErrorBoundary;
