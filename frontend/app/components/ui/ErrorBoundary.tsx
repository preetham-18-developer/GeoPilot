"use client";

import React, { Component, ReactNode } from "react";

interface Props {
  children: ReactNode;
  fallback?: ReactNode;
  componentName?: string;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: string;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: "" };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    this.setState({ errorInfo: info.componentStack ?? "" });
    console.error(`[ErrorBoundary] ${this.props.componentName ?? "Component"} crashed:`, error, info);
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null, errorInfo: "" });
  };

  handleReload = () => {
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;

      return (
        <div
          role="alert"
          style={{
            background: "var(--bg-card)",
            border: "1px solid rgba(239,68,68,0.25)",
            borderLeft: "4px solid var(--accent-red)",
            borderRadius: "var(--radius-card)",
            padding: "2rem",
            margin: "1rem 0",
          }}
        >
          <div className="flex items-center gap-3 mb-4">
            <svg
              width="22"
              height="22"
              viewBox="0 0 24 24"
              fill="none"
              stroke="var(--accent-red)"
              strokeWidth="2"
            >
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
            <h3 style={{ color: "var(--accent-red)", margin: 0, fontSize: "1rem" }}>
              {this.props.componentName
                ? `${this.props.componentName} failed to render`
                : "Something went wrong"}
            </h3>
          </div>

          {this.state.error && (
            <div
              style={{
                background: "rgba(0,0,0,0.3)",
                borderRadius: "var(--radius-md)",
                padding: "0.75rem 1rem",
                marginBottom: "1.25rem",
                fontFamily: "var(--font-mono)",
                fontSize: "0.8rem",
                color: "#FCA5A5",
                overflowX: "auto",
              }}
            >
              <div style={{ color: "var(--text-dark)", marginBottom: "0.25rem", fontSize: "0.72rem" }}>
                ERROR MESSAGE
              </div>
              {this.state.error.message}
            </div>
          )}

          <div className="flex gap-3">
            <button
              className="btn btn-secondary btn-sm"
              onClick={this.handleRetry}
            >
              <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
                <path d="M3 3v5h5" />
              </svg>
              Try Again
            </button>
            <button
              className="btn btn-ghost btn-sm"
              onClick={this.handleReload}
            >
              Reload Page
            </button>
          </div>

          {process.env.NODE_ENV === "development" && this.state.errorInfo && (
            <details style={{ marginTop: "1rem" }}>
              <summary
                style={{
                  color: "var(--text-dark)",
                  fontSize: "0.75rem",
                  cursor: "pointer",
                  userSelect: "none",
                }}
              >
                Component Stack (dev only)
              </summary>
              <pre
                style={{
                  color: "var(--text-dark)",
                  fontSize: "0.7rem",
                  overflow: "auto",
                  marginTop: "0.5rem",
                  whiteSpace: "pre-wrap",
                  wordBreak: "break-word",
                }}
              >
                {this.state.errorInfo}
              </pre>
            </details>
          )}
        </div>
      );
    }

    return this.props.children;
  }
}

/** Convenience wrapper for functional components */
export function withErrorBoundary<T extends object>(
  WrappedComponent: React.ComponentType<T>,
  componentName?: string
) {
  return function BoundaryWrapper(props: T) {
    return (
      <ErrorBoundary componentName={componentName ?? WrappedComponent.displayName ?? WrappedComponent.name}>
        <WrappedComponent {...props} />
      </ErrorBoundary>
    );
  };
}
