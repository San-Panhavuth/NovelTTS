import Link from "next/link";
import { requestPasswordReset } from "@/app/auth/actions";

type ForgotPasswordPageProps = {
  searchParams: Promise<{ message?: string }>;
};

export default async function ForgotPasswordPage({
  searchParams,
}: ForgotPasswordPageProps) {
  const { message } = await searchParams;

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-lg flex-col justify-center gap-6 px-6 py-12">
      <section className="space-y-2">
        <h1 className="text-3xl font-semibold tracking-tight">Reset password</h1>
        <p className="text-sm text-zinc-600 dark:text-zinc-400">
          Enter your account email and we&apos;ll send a reset link.
        </p>
        {message ? (
          <p className="rounded-md border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm dark:border-zinc-800 dark:bg-zinc-900">
            {message}
          </p>
        ) : null}
      </section>

      <form action={requestPasswordReset} className="space-y-3 rounded-lg border p-4">
        <input
          className="w-full rounded-md border px-3 py-2 text-sm"
          type="email"
          name="email"
          placeholder="you@example.com"
          required
        />
        <button className="w-full rounded-md bg-black px-3 py-2 text-sm text-white dark:bg-white dark:text-black">
          Send reset email
        </button>
      </form>

      <Link href="/login" className="text-sm text-zinc-600 underline dark:text-zinc-400">
        Back to login
      </Link>
    </main>
  );
}
