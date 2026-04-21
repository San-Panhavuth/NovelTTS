import Link from "next/link";
import { redirect } from "next/navigation";
import { SignOutForm } from "@/app/components/sign-out-form";
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

  let books: BookSummary[] = [];
  let loadError: string | null = null;
  try {
    books = await apiGetWithAuth<BookSummary[]>("/books");
  } catch (error) {
    loadError = error instanceof Error ? error.message : "Failed to load library.";
  }

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-5xl flex-col gap-6 px-6 py-10">
      <section className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">Your Library</h1>
          <p className="text-sm text-zinc-600 dark:text-zinc-400">
            Uploaded EPUB books for {user.email}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            href="/upload"
            className="rounded-md bg-black px-4 py-2 text-sm text-white dark:bg-white dark:text-black"
          >
            Upload EPUB
          </Link>
          <SignOutForm />
        </div>
      </section>

      <section className="space-y-3">
        {loadError ? <p className="rounded-lg border p-4 text-sm text-red-600">{loadError}</p> : null}
        {books.length === 0 ? (
          <p className="rounded-lg border p-4 text-sm">No books yet. Upload your first EPUB.</p>
        ) : (
          books.map((book) => (
            <Link
              key={book.id}
              href={`/books/${book.id}`}
              className="block rounded-lg border p-4 hover:bg-zinc-50 dark:hover:bg-zinc-900"
            >
              <h2 className="text-lg font-medium">{book.title}</h2>
              <p className="text-sm text-zinc-600 dark:text-zinc-400">
                {book.author || "Unknown author"} · {book.chapter_count} chapters
              </p>
            </Link>
          ))
        )}
      </section>
    </main>
  );
}
