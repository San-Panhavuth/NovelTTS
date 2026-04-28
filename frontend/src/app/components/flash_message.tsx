"use client";

import { useEffect, useMemo } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

type Variant = "success" | "warning" | "error";

const variantClasses: Record<Variant, string> = {
  success:
    "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-200",
  warning:
    "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200",
  error: "border-red-200 bg-red-50 text-red-800 dark:border-red-900 dark:bg-red-950 dark:text-red-200",
};

export function FlashMessage({ variant = "success" }: { variant?: Variant }) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const message = searchParams.get("message");
  const decoded = useMemo(() => {
    if (!message) return null;
    try {
      return decodeURIComponent(message);
    } catch {
      return message;
    }
  }, [message]);

  useEffect(() => {
    if (!message) return;
    const next = new URLSearchParams(searchParams.toString());
    next.delete("message");
    const query = next.toString();
    router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [message]);

  if (!decoded) return null;

  return (
    <div className={`mb-4 rounded-lg border px-4 py-3 text-sm ${variantClasses[variant]}`}>
      {decoded}
    </div>
  );
}

