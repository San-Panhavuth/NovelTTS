import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { PageShell } from "@/app/components/page-shell";
import { createSupabaseServerClient, isSupabaseConfigured } from "@/lib/supabase";
import {
  createBookPronunciation,
  deleteBookPronunciationEntry,
  inferBookPronunciationDictionary,
  updateBookPronunciationEntry,
} from "@/app/books/actions";
import { apiGetWithAuth } from "@/lib/backend";

type BookDetail = {
  id: string;
  title: string;
  author: string | null;
  origin_language: string | null;
};

type PronunciationEntry = {
  id: string;
  term: string;
  phoneme: string;
  language_code: string | null;
  created_at: string | null;
  updated_at: string | null;
};

type PronunciationsPageProps = {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ message?: string }>;
};

export default async function BookPronunciationsPage({ params, searchParams }: PronunciationsPageProps) {
  if (!isSupabaseConfigured()) redirect("/login?message=Supabase env is not configured.");

  const supabase = await createSupabaseServerClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) redirect("/login");

  const { id } = await params;
  const { message } = await searchParams;

  let book: BookDetail;
  try {
    book = await apiGetWithAuth<BookDetail>(`/books/${id}`);
  } catch {
    notFound();
  }

  const pronunciations = await apiGetWithAuth<{ entries: PronunciationEntry[]; total: number }>(
    `/books/${id}/pronunciations`
  ).catch(() => ({ entries: [], total: 0 }));

  return (
    <PageShell
      title="Pronunciation Dictionary"
      subtitle={`${book.title}${book.author ? ` · ${book.author}` : ""}`}
      maxWidth="xl"
      breadcrumbs={[
        { label: "Library", href: "/library" },
        { label: book.title, href: `/books/${id}` },
        { label: "Pronunciations" },
      ]}
      actions={
        <Link
          href={`/books/${id}/voice-settings`}
          className="rounded-lg border border-zinc-200 px-3 py-1.5 text-sm hover:bg-zinc-50 dark:border-zinc-700 dark:hover:bg-zinc-800"
        >
          Voice Settings
        </Link>
      }
    >
      {message && (
        <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800 dark:border-emerald-800 dark:bg-emerald-950 dark:text-emerald-200">
          {decodeURIComponent(message)}
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <section className="space-y-4 rounded-2xl border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-900">
          <div className="space-y-1">
            <h2 className="text-lg font-semibold">Inferred pronunciations</h2>
            <p className="text-sm text-zinc-500 dark:text-zinc-400">
              Fill this dictionary with terms that need special pronunciation, then let audio generation inject SSML.
            </p>
          </div>

          <form action={inferBookPronunciationDictionary} className="flex items-center gap-3">
            <input type="hidden" name="bookId" value={id} />
            <button
              type="submit"
              className="rounded-md bg-zinc-900 px-4 py-2 text-sm text-white hover:bg-zinc-700 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300"
            >
              Infer from segments
            </button>
            <span className="text-xs text-zinc-500">
              {pronunciations.total} saved pronunciation{pronunciations.total === 1 ? "" : "s"}
            </span>
          </form>

          {pronunciations.entries.length === 0 ? (
            <div className="rounded-xl border border-dashed border-zinc-300 p-6 text-sm text-zinc-500 dark:border-zinc-700">
              No pronunciations yet. Add one below or infer from the processed chapter text.
            </div>
          ) : (
            <div className="space-y-3">
              {pronunciations.entries.map((entry) => (
                <div key={entry.id} className="rounded-xl border border-zinc-200 p-4 dark:border-zinc-800">
                  <form action={updateBookPronunciationEntry} className="grid gap-3 md:grid-cols-[1fr_1fr_140px_auto] md:items-end">
                    <input type="hidden" name="bookId" value={id} />
                    <input type="hidden" name="entryId" value={entry.id} />
                    <label className="space-y-1 text-sm">
                      <span className="text-xs uppercase tracking-wide text-zinc-500">Term</span>
                      <input
                        name="term"
                        defaultValue={entry.term}
                        className="w-full rounded-md border border-zinc-200 bg-transparent px-3 py-2 text-sm dark:border-zinc-700"
                      />
                    </label>
                    <label className="space-y-1 text-sm">
                      <span className="text-xs uppercase tracking-wide text-zinc-500">Phoneme</span>
                      <input
                        name="phoneme"
                        defaultValue={entry.phoneme}
                        className="w-full rounded-md border border-zinc-200 bg-transparent px-3 py-2 text-sm dark:border-zinc-700"
                      />
                    </label>
                    <label className="space-y-1 text-sm">
                      <span className="text-xs uppercase tracking-wide text-zinc-500">Language</span>
                      <input
                        name="languageCode"
                        defaultValue={entry.language_code ?? ""}
                        placeholder="zh"
                        className="w-full rounded-md border border-zinc-200 bg-transparent px-3 py-2 text-sm dark:border-zinc-700"
                      />
                    </label>
                    <div className="flex gap-2">
                      <button
                        type="submit"
                        className="rounded-md bg-zinc-900 px-3 py-2 text-sm text-white hover:bg-zinc-700 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300"
                      >
                        Save
                      </button>
                      <button
                        formAction={deleteBookPronunciationEntry}
                        type="submit"
                        className="rounded-md border border-zinc-200 px-3 py-2 text-sm hover:bg-zinc-50 dark:border-zinc-700 dark:hover:bg-zinc-800"
                      >
                        Delete
                      </button>
                    </div>
                  </form>
                </div>
              ))}
            </div>
          )}
        </section>

        <section className="space-y-4 rounded-2xl border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-900">
          <div className="space-y-1">
            <h2 className="text-lg font-semibold">Add pronunciation</h2>
            <p className="text-sm text-zinc-500 dark:text-zinc-400">
              Enter a term once and reuse it across the book without rewriting the chapter text.
            </p>
          </div>

          <form action={createBookPronunciation} className="space-y-3">
            <input type="hidden" name="bookId" value={id} />
            <label className="block space-y-1 text-sm">
              <span className="text-xs uppercase tracking-wide text-zinc-500">Term</span>
              <input
                name="term"
                required
                placeholder="Ye Qing"
                className="w-full rounded-md border border-zinc-200 bg-transparent px-3 py-2 text-sm dark:border-zinc-700"
              />
            </label>
            <label className="block space-y-1 text-sm">
              <span className="text-xs uppercase tracking-wide text-zinc-500">Phoneme</span>
              <input
                name="phoneme"
                required
                placeholder="jeɪ tʃʰɪŋ"
                className="w-full rounded-md border border-zinc-200 bg-transparent px-3 py-2 text-sm dark:border-zinc-700"
              />
            </label>
            <label className="block space-y-1 text-sm">
              <span className="text-xs uppercase tracking-wide text-zinc-500">Language code</span>
              <input
                name="languageCode"
                placeholder="zh"
                className="w-full rounded-md border border-zinc-200 bg-transparent px-3 py-2 text-sm dark:border-zinc-700"
              />
            </label>
            <button
              type="submit"
              className="rounded-md bg-zinc-900 px-4 py-2 text-sm text-white hover:bg-zinc-700 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300"
            >
              Add entry
            </button>
          </form>

          <div className="rounded-xl border border-zinc-200 bg-zinc-50 p-4 text-sm text-zinc-600 dark:border-zinc-800 dark:bg-zinc-950 dark:text-zinc-400">
            Use IPA or a TTS-friendly phoneme spelling. The system will inject these terms before synthesis.
          </div>
        </section>
      </div>
    </PageShell>
  );
}