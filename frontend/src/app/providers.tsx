"use client";

import { TooltipProvider } from "@/components/ui/tooltip";
import { AppStateProvider } from "@/hooks/useAppState";

export default function Providers({ children }: { children: React.ReactNode }) {
  return (
    <AppStateProvider>
      <TooltipProvider>{children}</TooltipProvider>
    </AppStateProvider>
  );
}
