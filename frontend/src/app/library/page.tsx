import Link from "next/link";
import { redirect } from "next/navigation";
import { PageShell } from "@/app/components/page-shell";
import { createSupabaseServerClient, isSupabaseConfigured } from "@/lib/supabase";
import { apiGetWithAuth } from "@/lib/backend";

type BookSummary = {
  id: string;
  title: string;
  author: string | null;
  chapter_count: number;
  created_at: string;
};

export default async function LibraryPage() {
  if (!isSupabaseConfigured()) redirect("/login?message=Supabase env is not configured.");

  const supabase = await createSupabaseServerClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect("/login");

  let books: BookSummary[] = [];
  let loadError: string | null = null;
  try {
    books = await apiGetWithAuth<BookSummary[]>("/books");
  } catch (error) {
    loadError = error instanceof Error ? error.message : "Failed to load library.";
  }

  return (
    <PageShell
      title="Your Library"
      subtitle={user.email ?? undefined}
      maxWidth="xl"
      actions={
        <Link
          href="/upload"
          className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
        >
          + Upload EPUB
        </Link>
      }
    >
      {loadError && (
        <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
          {loadError}
        </div>
      )}

      {books.length === 0 ? (
        <div className="flex flex-col items-center justify-center rounded-2xl border-2 border-dashed border-zinc-200 py-20 text-center dark:border-zinc-800">
          <p className="text-sm font-medium text-zinc-500">No books yet</p>
          <p className="mt-1 text-xs text-zinc-400">Upload an EPUB to get started</p>
          <Link
            href="/upload"
            className="mt-4 rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
          >
            Upload EPUB
          </Link>
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {books.map((book) => (
            <Link
              key={book.id}
              href={`/books/${book.id}`}
              className="group flex flex-col gap-3 rounded-xl border border-zinc-200 bg-white p-5 hover:border-indigo-300 hover:shadow-sm dark:border-zinc-800 dark:bg-zinc-900 dark:hover:border-indigo-700"
            >
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-50 text-lg dark:bg-indigo-950">
                📖
              </div>
              <div className="flex-1">
                <h2 className="font-semibold leading-tight group-hover:text-indigo-600 dark:group-hover:text-indigo-400">
                  {book.title}
                </h2>
                <p className="mt-0.5 text-xs text-zinc-500">
                  {book.author ?? "Unknown author"}
                </p>
              </div>
              <p className="text-xs text-zinc-400">{book.chapter_count} chapters</p>
            </Link>
          ))}
        </div>
      )}
    </PageShell>
  );
}
