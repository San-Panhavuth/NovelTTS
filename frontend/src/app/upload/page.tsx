import Link from "next/link";
import { redirect } from "next/navigation";
import { uploadEpub } from "@/app/upload/actions";
import { SignOutForm } from "@/app/components/sign-out-form";
import { createSupabaseServerClient, isSupabaseConfigured } from "@/lib/supabase";

type UploadPageProps = {
  searchParams: Promise<{ message?: string }>;
};

export default async function UploadPage({ searchParams }: UploadPageProps) {
  if (!isSupabaseConfigured()) {
    redirect("/login?message=Supabase env is not configured.");
  }

  const supabase = await createSupabaseServerClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/login");
  }

  const { message } = await searchParams;

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-3xl flex-col gap-6 px-6 py-12">
      <section className="flex items-start justify-between gap-4">
        <div className="space-y-2">
          <h1 className="text-3xl font-semibold tracking-tight">Upload EPUB</h1>
          <p className="text-sm text-zinc-600 dark:text-zinc-400">Max 50MB. EPUB only.</p>
        </div>
        <SignOutForm />
      </section>

      {message ? <p className="rounded-md border px-3 py-2 text-sm">{message}</p> : null}

      <form action={uploadEpub} className="space-y-4 rounded-lg border p-4">
        <input
          type="file"
          name="file"
          accept=".epub,application/epub+zip"
          className="w-full rounded-md border px-3 py-2 text-sm"
          required
        />
        <button className="rounded-md bg-black px-4 py-2 text-sm text-white dark:bg-white dark:text-black">
          Upload and parse
        </button>
      </form>

      <Link href="/library" className="text-sm underline">
        Back to library
      </Link>
    </main>
  );
}
