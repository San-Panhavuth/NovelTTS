import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { PageShell } from "@/app/components/page-shell";
import { FlashMessage } from "@/app/components/flash_message";
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
  const { data: { user } } = await supabase.auth.getUser();
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
      {message && <FlashMessage variant="success" />}

      <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
        {/* Left — entry list */}
        <section className="rounded-2xl border border-zinc-200 bg-white dark:border-zinc-800 dark:bg-zinc-900">
          {/* Header + infer CTA */}
          <div className="flex flex-col gap-4 border-b border-zinc-200 p-5 dark:border-zinc-800 sm:flex-row sm:items-start sm:justify-between">
            <div className="space-y-1">
              <h2 className="text-base font-semibold">Saved pronunciations</h2>
              <p className="text-xs text-zinc-500 dark:text-zinc-400">
                {pronunciations.total === 0
                  ? "No entries yet."
                  : `${pronunciations.total} term${pronunciations.total === 1 ? "" : "s"} saved.`}{" "}
                Applied during audio generation.
              </p>
            </div>
            <form action={inferBookPronunciationDictionary} className="shrink-0">
              <input type="hidden" name="bookId" value={id} />
              <button
                type="submit"
                className="w-full rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 sm:w-auto"
              >
                Infer from segments
              </button>
            </form>
          </div>

          {/* Entry list */}
          <div className="p-5">
            {pronunciations.entries.length === 0 ? (
              <div className="rounded-xl border border-dashed border-zinc-300 px-6 py-10 text-center text-sm text-zinc-400 dark:border-zinc-700">
                No pronunciations yet. Add one using the form, or click{" "}
                <span className="font-medium text-zinc-600 dark:text-zinc-300">Infer from segments</span>{" "}
                to auto-populate from processed chapter text.
              </div>
            ) : (
              <div className="space-y-3">
                {pronunciations.entries.map((entry) => (
                  <div
                    key={entry.id}
                    className="rounded-xl border border-zinc-200 bg-zinc-50 p-4 dark:border-zinc-700 dark:bg-zinc-800/50"
                  >
                    <form action={updateBookPronunciationEntry} className="space-y-3">
                      <input type="hidden" name="bookId" value={id} />
                      <input type="hidden" name="entryId" value={entry.id} />

                      {/* Row 1: term + phoneme */}
                      <div className="grid gap-3 sm:grid-cols-2">
                        <label className="space-y-1.5">
                          <span className="text-xs font-medium uppercase tracking-wide text-zinc-500">Term</span>
                          <input
                            name="term"
                            defaultValue={entry.term}
                            className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2.5 text-sm dark:border-zinc-700 dark:bg-zinc-900"
                          />
                        </label>
                        <label className="space-y-1.5">
                          <span className="text-xs font-medium uppercase tracking-wide text-zinc-500">Phoneme</span>
                          <input
                            name="phoneme"
                            defaultValue={entry.phoneme}
                            className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2.5 text-sm dark:border-zinc-700 dark:bg-zinc-900"
                          />
                        </label>
                      </div>

                      {/* Row 2: language + actions */}
                      <div className="flex flex-wrap items-end gap-3">
                        <label className="space-y-1.5">
                          <span className="text-xs font-medium uppercase tracking-wide text-zinc-500">Language</span>
                          <input
                            name="languageCode"
                            defaultValue={entry.language_code ?? ""}
                            placeholder="zh"
                            className="w-28 rounded-lg border border-zinc-200 bg-white px-3 py-2.5 text-sm dark:border-zinc-700 dark:bg-zinc-900"
                          />
                        </label>
                        <div className="flex gap-2 pb-0.5">
                          <button
                            type="submit"
                            className="rounded-lg bg-zinc-900 px-4 py-2 text-sm text-white hover:bg-zinc-700 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300"
                          >
                            Save
                          </button>
                          <button
                            formAction={deleteBookPronunciationEntry}
                            type="submit"
                            className="rounded-lg border border-zinc-200 px-4 py-2 text-sm text-zinc-600 hover:bg-red-50 hover:border-red-200 hover:text-red-600 dark:border-zinc-700 dark:text-zinc-400 dark:hover:bg-red-950 dark:hover:border-red-800 dark:hover:text-red-400"
                          >
                            Delete
                          </button>
                        </div>
                      </div>
                    </form>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>

        {/* Right — add form */}
        <section className="rounded-2xl border border-zinc-200 bg-zinc-50 dark:border-zinc-800 dark:bg-zinc-900/50">
          <div className="border-b border-zinc-200 p-5 dark:border-zinc-800">
            <h2 className="text-base font-semibold">Add pronunciation</h2>
            <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">
              Enter a term once — it&apos;s reused across the book without rewriting chapter text.
            </p>
          </div>

          <div className="p-5">
            <form action={createBookPronunciation} className="space-y-4">
              <input type="hidden" name="bookId" value={id} />

              <label className="block space-y-1.5">
                <span className="text-xs font-medium uppercase tracking-wide text-zinc-500">Term</span>
                <input
                  name="term"
                  required
                  placeholder="Ye Qing"
                  className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2.5 text-sm dark:border-zinc-700 dark:bg-zinc-900"
                />
              </label>

              <label className="block space-y-1.5">
                <span className="text-xs font-medium uppercase tracking-wide text-zinc-500">Phoneme</span>
                <input
                  name="phoneme"
                  required
                  placeholder="jeɪ tʃʰɪŋ"
                  className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2.5 text-sm dark:border-zinc-700 dark:bg-zinc-900"
                />
              </label>

              <label className="block space-y-1.5">
                <span className="text-xs font-medium uppercase tracking-wide text-zinc-500">Language code</span>
                <input
                  name="languageCode"
                  placeholder="zh"
                  className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2.5 text-sm dark:border-zinc-700 dark:bg-zinc-900"
                />
              </label>

              <button
                type="submit"
                className="w-full rounded-lg bg-zinc-900 px-4 py-2.5 text-sm font-medium text-white hover:bg-zinc-700 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300"
              >
                Add entry
              </button>
            </form>

            <div className="mt-4 rounded-lg border border-zinc-200 bg-white p-3 text-xs text-zinc-500 dark:border-zinc-700 dark:bg-zinc-900">
              Use IPA or a TTS-friendly phoneme spelling. The system substitutes these terms before synthesis.
            </div>
          </div>
        </section>
      </div>
    </PageShell>
  );
}
