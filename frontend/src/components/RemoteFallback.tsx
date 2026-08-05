import { Component, type ReactNode } from "react";
import { AlertCircle } from "lucide-react";

interface Props {
  children: ReactNode;
  name: string;
}

interface State {
  hasError: boolean;
}

export class RemoteBoundary extends Component<Props, State> {
  state: State = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="rounded-lg border border-border bg-background p-8 text-center">
          <AlertCircle className="mx-auto mb-3 h-8 w-8 text-muted-foreground" />
          <p className="text-sm font-medium text-foreground">
            {this.props.name} is temporarily unavailable
          </p>
          <p className="mt-1 text-sm text-muted-foreground">
            Please try again later.
          </p>
        </div>
      );
    }
    return this.props.children;
  }
}
