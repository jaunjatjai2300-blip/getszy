import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Command, CommandInput, CommandList, CommandItem, CommandGroup, CommandEmpty } from "@/components/ui/command";
import { Dialog, DialogContent } from "@/components/ui/dialog";
import { Sparkles, Film, PenTool, Globe, Youtube, TrendingUp, Package, Users, Rocket, Layers, GraduationCap, Settings, FlaskConical, Briefcase } from "lucide-react";
import { useAuth } from "@/lib/auth";

// Global Cmd+K palette. Works across the whole app.
export default function CommandPalette() {
  const [open, setOpen] = useState(false);
  const nav = useNavigate();
  const { user } = useAuth();

  useEffect(() => {
    const handler = (e) => {
      if ((e.key === "k" || e.key === "K") && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setOpen((o) => !o);
      }
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  const go = (path) => { setOpen(false); nav(path); };
  const isAdmin = user?.role === "admin";
  const isFounder = user?.role === "founder" || isAdmin;

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogContent className="p-0 max-w-xl" data-testid="command-palette">
        <Command>
          <CommandInput placeholder="Type a command or search…" data-testid="cmdk-input"/>
          <CommandList>
            <CommandEmpty>Nothing found.</CommandEmpty>
            <CommandGroup heading="Neo">
              <CommandItem onSelect={() => go("/dashboard")}><Sparkles className="mr-2 h-4 w-4"/>New chat</CommandItem>
              <CommandItem onSelect={() => go("/dashboard/projects")}><Layers className="mr-2 h-4 w-4"/>All projects</CommandItem>
            </CommandGroup>
            <CommandGroup heading="Create">
              <CommandItem onSelect={() => go("/dashboard")}><Film className="mr-2 h-4 w-4"/>Generate a video</CommandItem>
              <CommandItem onSelect={() => go("/dashboard")}><PenTool className="mr-2 h-4 w-4"/>Write a script</CommandItem>
              <CommandItem onSelect={() => go("/dashboard")}><Globe className="mr-2 h-4 w-4"/>Build a web app</CommandItem>
              <CommandItem onSelect={() => go("/dashboard")}><Youtube className="mr-2 h-4 w-4"/>Plan a channel</CommandItem>
              <CommandItem onSelect={() => go("/dashboard")}><TrendingUp className="mr-2 h-4 w-4"/>Predict trends</CommandItem>
            </CommandGroup>
            {isFounder && (
              <CommandGroup heading="Labs">
                <CommandItem onSelect={() => go("/labs")}><FlaskConical className="mr-2 h-4 w-4"/>Internal Labs</CommandItem>
              </CommandGroup>
            )}
            {isAdmin && (
              <CommandGroup heading="Admin">
                <CommandItem onSelect={() => go("/admin")}><Settings className="mr-2 h-4 w-4"/>Overview</CommandItem>
                <CommandItem onSelect={() => go("/admin/products")}><Package className="mr-2 h-4 w-4"/>Products</CommandItem>
                <CommandItem onSelect={() => go("/admin/customers")}><Users className="mr-2 h-4 w-4"/>Customers</CommandItem>
                <CommandItem onSelect={() => go("/admin/courses")}><GraduationCap className="mr-2 h-4 w-4"/>Courses</CommandItem>
                <CommandItem onSelect={() => go("/admin/workforce")}><Briefcase className="mr-2 h-4 w-4"/>AI Workforce</CommandItem>
                <CommandItem onSelect={() => go("/admin/deploy")}><Rocket className="mr-2 h-4 w-4"/>Deploy</CommandItem>
              </CommandGroup>
            )}
            <CommandGroup heading="Storefront">
              <CommandItem onSelect={() => go("/shop")}><Package className="mr-2 h-4 w-4"/>Shop</CommandItem>
            </CommandGroup>
          </CommandList>
        </Command>
      </DialogContent>
    </Dialog>
  );
}
