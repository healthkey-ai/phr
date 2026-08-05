import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
  label?: string;
}

interface State {
  error: Error | null;
}

// Catches errors from lazily-loaded federated remotes (and their render) so a
// failure shows a message instead of a blank white screen.
export class RemoteErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("RemoteErrorBoundary caught:", error, info);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="rounded-lg border border-destructive/40 bg-destructive/10 p-4 text-sm">
          <p className="font-medium text-destructive">
            {this.props.label ?? "Failed to load this section"}
          </p>
          <pre className="mt-2 whitespace-pre-wrap break-words text-xs text-muted-foreground">
            {this.state.error.message}
          </pre>
        </div>
      );
    }
    return this.props.children;
  }
}
