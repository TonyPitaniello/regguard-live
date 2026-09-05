import { Component, type ErrorInfo, type ReactNode } from 'react';
import { AlertCircle } from 'lucide-react';

type Props = {
  children: ReactNode;
  fallback?: ReactNode;
  /** Called when the user chooses Try again / Go home recovery. */
  onReset?: () => void;
};

type State = {
  hasError: boolean;
  error?: Error;
};

/**
 * Prevents a single render crash from blanking the whole RegGuard shell
 * (dark navy #root with no UI).
 */
export class ErrorBoundary extends Component<Props, State> {
  override state: State = { hasError: false };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  override componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
    console.error('[RegGuard ErrorBoundary]', error, errorInfo.componentStack);
  }

  private reset = () => {
    this.setState({ hasError: false, error: undefined });
    this.props.onReset?.();
  };

  override render(): ReactNode {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback;
      return (
        <div className="w-full rounded-2xl border border-red-500/40 bg-red-500/10 p-6 sm:p-8 text-center">
          <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-3" />
          <h2 className="text-xl font-bold text-white mb-2">Results view hit a snag</h2>
          <p className="text-gray-300 text-sm mb-4">
            The site research finished, but the results panel could not render. Your form is still
            available — try again or reload.
          </p>
          {this.state.error ? (
            <p className="text-xs text-gray-500 font-mono mb-4 break-all">{this.state.error.message}</p>
          ) : null}
          <div className="flex flex-col sm:flex-row gap-2 justify-center">
            <button
              type="button"
              onClick={this.reset}
              className="px-5 py-2.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-bold"
            >
              Back to form
            </button>
            <button
              type="button"
              onClick={() => window.location.assign('/')}
              className="px-5 py-2.5 rounded-lg border border-slate-500 bg-slate-900/60 hover:bg-slate-800 text-white text-sm font-semibold"
            >
              Reload home
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
