import Link from "next/link";
import { requestPasswordReset } from "@/app/auth/actions";

type ForgotPasswordPageProps = {
  searchParams: Promise<{ message?: string }>;
};

export default async function ForgotPasswordPage({ searchParams }: ForgotPasswordPageProps) {
  const { message } = await searchParams;

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-zinc-50 px-4 dark:bg-zinc-950">
      <div className="w-full max-w-sm space-y-6">
        <div className="text-center">
          <h1 className="text-2xl font-bold tracking-tight">Reset password</h1>
          <p className="mt-1 text-sm text-zinc-500">
            We&apos;ll send a reset link to your email.
          </p>
        </div>

        {message && (
          <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200">
            {message}
          </div>
        )}

        <div className="rounded-2xl border border-zinc-200 bg-white p-6 shadow-sm dark:border-zinc-800 dark:bg-zinc-900">
          <form action={requestPasswordReset} className="space-y-3">
            <input
              type="email"
              name="email"
              placeholder="Email"
              required
              className="w-full rounded-lg border border-zinc-200 bg-transparent px-3 py-2.5 text-sm placeholder-zinc-400 focus:border-indigo-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/20 dark:border-zinc-700"
            />
            <button
              type="submit"
              className="w-full rounded-lg bg-indigo-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-indigo-700"
            >
              Send reset link
            </button>
          </form>
        </div>

        <p className="text-center text-sm text-zinc-500">
          <Link href="/login" className="hover:text-zinc-900 dark:hover:text-zinc-100">
            ← Back to sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
