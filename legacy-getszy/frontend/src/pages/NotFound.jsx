import { Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Compass } from "lucide-react";

export default function NotFound() {
  return (
    <div className="min-h-[70vh] flex items-center justify-center px-6 text-center" data-testid="not-found-page">
      <div>
        <Compass className="h-10 w-10 mx-auto mb-4 text-[var(--gs-primary)]" />
        <h1 className="font-display text-4xl mb-2">Page not found</h1>
        <p className="text-[var(--gs-muted)] mb-6 max-w-md mx-auto">
          Ye page exist nahi karta ya move ho gaya hai.
        </p>
        <Link to="/">
          <Button className="bg-[var(--gs-primary)] hover:bg-[var(--gs-primary-2)]">Go home</Button>
        </Link>
      </div>
    </div>
  );
}
