import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw, Home } from 'lucide-react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen flex-col items-center justify-center gap-4" style={{ background: 'var(--bg-base)', color: 'var(--text-primary)' }}>
          <AlertTriangle className="h-12 w-12" style={{ color: 'var(--error)' }} />
          <h1 className="text-xl font-semibold">Something went wrong</h1>
          <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
            {this.state.error?.message || 'An unexpected error occurred'}
          </p>
          <div className="flex gap-3">
            <button
              onClick={() => window.location.reload()}
              className="flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium text-white"
              style={{ background: 'var(--accent)' }}
            >
              <RefreshCw className="h-4 w-4" />
              Reload
            </button>
            <button
              onClick={() => { this.setState({ hasError: false, error: null }); window.location.href = '/'; }}
              className="flex items-center gap-2 rounded-lg px-4 py-2 text-sm font-medium"
              style={{ background: 'var(--glass-bg)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
            >
              <Home className="h-4 w-4" />
              Go Home
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
