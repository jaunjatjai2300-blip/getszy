import { Component } from "react";
import { Button } from "@/components/ui/button";
import { AlertTriangle } from "lucide-react";

export class ErrorBoundary extends Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, info) {
    console.error("Unhandled UI error:", error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center px-6 text-center">
          <div>
            <AlertTriangle className="h-10 w-10 mx-auto mb-4 text-[var(--gs-primary)]" />
            <h1 className="font-display text-2xl mb-2">Something went wrong</h1>
            <p className="text-[var(--gs-muted)] mb-6">
              Kuch gadbad ho gayi. Please refresh the page and try again.
            </p>
            <Button
              onClick={() => window.location.reload()}
              className="bg-[var(--gs-primary)] hover:bg-[var(--gs-primary-2)]"
            >
              Reload page
            </Button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
