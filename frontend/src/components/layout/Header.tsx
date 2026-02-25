"use client";

interface HeaderProps {
  title: string;
  breadcrumb?: string;
  subtitle?: string;
  badge?: string;
  children?: React.ReactNode;
}

export default function Header({
  title,
  breadcrumb,
  subtitle,
  badge,
  children,
}: HeaderProps) {
  return (
    <div className="flex items-start justify-between pb-6">
      <div>
        {breadcrumb && (
          <p className="mb-1 font-mono text-[11px] uppercase tracking-[0.2em] text-cyan">
            {breadcrumb}
          </p>
        )}
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-white">{title}</h1>
          {badge && (
            <span className="rounded-md bg-white/[0.06] px-2 py-0.5 font-mono text-[10px] text-muted-foreground">
              {badge}
            </span>
          )}
        </div>
        {subtitle && (
          <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>
        )}
      </div>
      <div className="flex items-center gap-2">{children}</div>
    </div>
  );
}
