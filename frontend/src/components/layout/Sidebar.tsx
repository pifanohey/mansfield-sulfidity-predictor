"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  SlidersHorizontal,
  BarChart3,
  GitCompare,
} from "lucide-react";

const NAV = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/inputs", label: "Inputs", icon: SlidersHorizontal },
  { href: "/results", label: "Results", icon: BarChart3 },
  { href: "/scenarios", label: "Scenarios", icon: GitCompare },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex h-screen w-56 flex-col border-r bg-card">
      <div className="flex h-14 items-center border-b px-4">
        <span className="text-lg font-bold tracking-tight">
          Sulfidity
        </span>
      </div>
      <nav className="flex-1 space-y-1 p-2">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
              )}
            >
              <Icon className="h-4 w-4" />
              {label}
            </Link>
          );
        })}
      </nav>
      <div className="border-t p-4 text-xs text-muted-foreground">
        Pine Hill Mill v1.0
      </div>
    </aside>
  );
}
