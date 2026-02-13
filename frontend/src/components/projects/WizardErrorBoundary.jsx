import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

class WizardErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    if (import.meta.env.DEV) {
        console.error('Wizard Error:', error, errorInfo);
    }
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null });
    // Optional: Call a prop to reset wizard state if needed
    if (this.props.onRetry) {
        this.props.onRetry();
    }
  };

  render() {
    if (this.state.hasError) {
      return (
        <div className="h-full flex flex-col items-center justify-center p-8 text-center animate-in fade-in">
          <div className="w-16 h-16 bg-red-500/10 rounded-full flex items-center justify-center mb-4">
            <AlertTriangle className="w-8 h-8 text-red-500" />
          </div>
          <h3 className="text-lg font-bold text-white mb-2">Something went wrong</h3>
          <p className="text-slate-400 mb-6 max-w-sm">
            The wizard encountered an unexpected error. Please try again or restart the application.
          </p>
          <div className="bg-red-950/30 border border-red-900/50 rounded-lg p-3 mb-6 max-w-lg w-full overflow-auto text-left">
             <code className="text-xs font-mono text-red-300">
                {this.state.error?.toString()}
             </code>
          </div>
          <button
            onClick={this.handleRetry}
            className="flex items-center gap-2 px-4 py-2 bg-white/10 hover:bg-white/20 text-white rounded-lg transition-colors"
          >
            <RefreshCw size={16} />
            Try Again
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

export default WizardErrorBoundary;
