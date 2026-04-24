import { redirect } from "next/navigation";
import { PageShell } from "@/app/components/page-shell";
import { uploadEpub } from "@/app/upload/actions";
import { createSupabaseServerClient, isSupabaseConfigured } from "@/lib/supabase";

type UploadPageProps = {
  searchParams: Promise<{ message?: string }>;
};

export default async function UploadPage({ searchParams }: UploadPageProps) {
  if (!isSupabaseConfigured()) redirect("/login?message=Supabase env is not configured.");

  const supabase = await createSupabaseServerClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect("/login");

  const { message } = await searchParams;

  return (
    <PageShell
      title="Upload EPUB"
      subtitle="Max 50 MB · EPUB only"
      maxWidth="md"
      breadcrumbs={[{ label: "Library", href: "/library" }, { label: "Upload" }]}
    >
      {message && (
        <div className="mb-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-950 dark:text-amber-200">
          {decodeURIComponent(message)}
        </div>
      )}

      <form action={uploadEpub} className="rounded-xl border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-900">
        <label className="block space-y-2">
          <span className="text-sm font-medium">EPUB file</span>
          <input
            type="file"
            name="file"
            accept=".epub,application/epub+zip"
            required
            className="block w-full cursor-pointer rounded-lg border border-zinc-200 bg-zinc-50 px-3 py-2 text-sm text-zinc-600 file:mr-3 file:cursor-pointer file:rounded-md file:border-0 file:bg-indigo-600 file:px-3 file:py-1.5 file:text-xs file:font-medium file:text-white hover:file:bg-indigo-700 dark:border-zinc-700 dark:bg-zinc-800 dark:text-zinc-400"
          />
        </label>

        <button
          type="submit"
          className="mt-4 rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-medium text-white hover:bg-indigo-700"
        >
          Upload and parse
        </button>
      </form>
    </PageShell>
  );
}
