import type { ReactNode } from "react";
import Link from "next/link";
import { SignOutForm } from "./sign-out-form";

type BreadcrumbItem = { label: string; href?: string };

type PageShellProps = {
  title: string;
  subtitle?: string;
  breadcrumbs?: BreadcrumbItem[];
  actions?: ReactNode;
  children: ReactNode;
  maxWidth?: "sm" | "md" | "lg" | "xl";
};

const widthMap = {
  sm: "max-w-sm",
  md: "max-w-2xl",
  lg: "max-w-4xl",
  xl: "max-w-6xl",
};

export function PageShell({
  title,
  subtitle,
  breadcrumbs,
  actions,
  children,
  maxWidth = "lg",
}: PageShellProps) {
  return (
    <div className="min-h-screen">
      <nav className="sticky top-0 z-10 border-b border-zinc-200 bg-white/80 backdrop-blur dark:border-zinc-800 dark:bg-zinc-950/80">
        <div className={`mx-auto flex h-14 ${widthMap[maxWidth]} items-center justify-between px-6`}>
          <Link href="/library" className="text-sm font-semibold tracking-tight">
            NovelTTS
          </Link>
          <SignOutForm />
        </div>
      </nav>

      <main className={`mx-auto ${widthMap[maxWidth]} px-6 py-8`}>
        {breadcrumbs && breadcrumbs.length > 0 && (
          <nav className="mb-4 flex items-center gap-1.5 text-xs text-zinc-500">
            {breadcrumbs.map((crumb, i) => (
              <span key={i} className="flex items-center gap-1.5">
                {i > 0 && <span>/</span>}
                {crumb.href ? (
                  <Link href={crumb.href} className="hover:text-zinc-900 dark:hover:text-zinc-100">
                    {crumb.label}
                  </Link>
                ) : (
                  <span className="text-zinc-900 dark:text-zinc-100">{crumb.label}</span>
                )}
              </span>
            ))}
          </nav>
        )}

        <div className="mb-6 flex items-start justify-between gap-4">
          <div className="space-y-1">
            <h1 className="text-2xl font-semibold tracking-tight">{title}</h1>
            {subtitle && (
              <p className="text-sm text-zinc-500 dark:text-zinc-400">{subtitle}</p>
            )}
          </div>
          {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
        </div>

        {children}
      </main>
    </div>
  );
}
