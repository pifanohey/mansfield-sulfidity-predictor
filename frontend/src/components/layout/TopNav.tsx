"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { useMillConfig } from "@/hooks/useMillConfig";
import {
  LayoutDashboard,
  SlidersHorizontal,
  BarChart3,
  GitCompare,
  Settings,
} from "lucide-react";

const NAV = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/inputs", label: "Inputs", icon: SlidersHorizontal },
  { href: "/results", label: "Results", icon: BarChart3 },
  { href: "/scenarios", label: "Scenarios", icon: GitCompare },
];

export default function TopNav() {
  const pathname = usePathname();
  const { config } = useMillConfig();
  const millName = config?.mill_name ?? "Mill";
  const initials = millName.split(" ").map(w => w[0]).join("").slice(0, 2).toUpperCase();

  return (
    <header className="sticky top-0 z-50 flex h-14 items-center justify-between border-b border-white/[0.06] bg-background/95 px-6 backdrop-blur-sm">
      {/* Logo + Nav */}
      <div className="flex items-center gap-8">
        {/* Brand */}
        <Link href="/" className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary">
            <span className="text-xs font-bold text-white">S</span>
          </div>
          <span className="text-sm font-bold tracking-tight text-white">
            Simulator
          </span>
        </Link>

        {/* Nav Links */}
        <nav className="flex items-center gap-1">
          {NAV.map(({ href, label, icon: Icon }) => {
            const active = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  "flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition-all",
                  active
                    ? "bg-primary text-white"
                    : "text-muted-foreground hover:bg-white/[0.06] hover:text-white"
                )}
              >
                <Icon className="h-3.5 w-3.5" />
                {label}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Right Side */}
      <div className="flex items-center gap-3">
        <span className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
          {millName} Mill
        </span>
        <div className="h-4 w-px bg-white/10" />
        <button className="rounded-lg p-1.5 text-muted-foreground transition-colors hover:bg-white/[0.06] hover:text-white">
          <Settings className="h-4 w-4" />
        </button>
        <div className="flex h-7 w-7 items-center justify-center rounded-full bg-primary/20 text-xs font-bold text-primary">
          {initials}
        </div>
      </div>
    </header>
  );
}
