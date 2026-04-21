import Link from "next/link";
import {
  signInWithGoogle,
  signInWithPassword,
  signUpWithPassword,
} from "@/app/auth/actions";

type LoginPageProps = {
  searchParams: Promise<{ message?: string }>;
};

export default async function LoginPage({ searchParams }: LoginPageProps) {
  const { message } = await searchParams;

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-3xl flex-col justify-center gap-8 px-6 py-12">
      <section className="space-y-3">
        <h1 className="text-3xl font-semibold tracking-tight">NovelTTS Auth</h1>
        <p className="text-sm text-zinc-600 dark:text-zinc-400">
          Sign in or create your account to start uploading EPUB files.
        </p>
        {message ? (
          <p className="rounded-md border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm dark:border-zinc-800 dark:bg-zinc-900">
            {message}
          </p>
        ) : null}
      </section>

      <section className="grid gap-6 md:grid-cols-2">
        <form action={signInWithPassword} className="space-y-3 rounded-lg border p-4">
          <h2 className="text-lg font-medium">Sign in</h2>
          <input
            className="w-full rounded-md border px-3 py-2 text-sm"
            type="email"
            name="email"
            placeholder="you@example.com"
            required
          />
          <input
            className="w-full rounded-md border px-3 py-2 text-sm"
            type="password"
            name="password"
            placeholder="Password"
            required
          />
          <button className="w-full rounded-md bg-black px-3 py-2 text-sm text-white dark:bg-white dark:text-black">
            Sign in with email
          </button>
        </form>

        <form action={signUpWithPassword} className="space-y-3 rounded-lg border p-4">
          <h2 className="text-lg font-medium">Create account</h2>
          <input
            className="w-full rounded-md border px-3 py-2 text-sm"
            type="email"
            name="email"
            placeholder="you@example.com"
            required
          />
          <input
            className="w-full rounded-md border px-3 py-2 text-sm"
            type="password"
            name="password"
            placeholder="Password"
            minLength={8}
            required
          />
          <button className="w-full rounded-md bg-black px-3 py-2 text-sm text-white dark:bg-white dark:text-black">
            Sign up with email
          </button>
        </form>
      </section>

      <section className="space-y-3 rounded-lg border p-4">
        <h2 className="text-lg font-medium">Social sign-in</h2>
        <form action={signInWithGoogle}>
          <button className="rounded-md border px-4 py-2 text-sm">
            Continue with Google
          </button>
        </form>
      </section>

      <Link
        href="/forgot-password"
        className="text-sm text-zinc-600 underline dark:text-zinc-400"
      >
        Forgot password?
      </Link>
    </main>
  );
}
