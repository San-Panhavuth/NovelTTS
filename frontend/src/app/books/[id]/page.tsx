import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { PageShell } from "@/app/components/page-shell";
import { createSupabaseServerClient, isSupabaseConfigured } from "@/lib/supabase";
import { apiGetWithAuth } from "@/lib/backend";

type Chapter = {
  id: string;
  chapter_idx: number;
  title: string | null;
  status: string;
};

type BookDetail = {
  id: string;
  title: string;
  author: string | null;
  origin_language: string | null;
  chapters: Chapter[];
};

type BookDetailPageProps = {
  params: Promise<{ id: string }>;
};

const statusBadge: Record<string, string> = {
  uploaded: "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400",
  processing: "bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-300",
  processed: "bg-green-50 text-green-700 dark:bg-green-950 dark:text-green-300",
  generating: "bg-amber-50 text-amber-700 dark:bg-amber-950 dark:text-amber-300",
  done: "bg-indigo-50 text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300",
  failed: "bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-300",
};

export default async function BookDetailPage({ params }: BookDetailPageProps) {
  if (!isSupabaseConfigured()) redirect("/login?message=Supabase env is not configured.");

  const supabase = await createSupabaseServerClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect("/login");

  const { id } = await params;

  try {
    const book = await apiGetWithAuth<BookDetail>(`/books/${id}`);

    return (
      <PageShell
        title={book.title}
        subtitle={[book.author, book.origin_language].filter(Boolean).join(" · ") || undefined}
        maxWidth="xl"
        breadcrumbs={[{ label: "Library", href: "/library" }, { label: book.title }]}
        actions={
          <Link
            href={`/books/${book.id}/voice-settings`}
            className="rounded-lg border border-zinc-200 px-3 py-1.5 text-sm hover:bg-zinc-50 dark:border-zinc-700 dark:hover:bg-zinc-800"
          >
            🎙 Voice Settings
          </Link>
        }
      >
        <div className="space-y-2">
          {book.chapters.map((chapter) => (
            <Link
              key={chapter.id}
              href={`/books/${book.id}/chapters/${chapter.chapter_idx}`}
              className="flex items-center justify-between rounded-xl border border-zinc-200 bg-white px-5 py-4 hover:border-indigo-300 hover:shadow-sm dark:border-zinc-800 dark:bg-zinc-900 dark:hover:border-indigo-700"
            >
              <div>
                <span className="font-medium">
                  Chapter {chapter.chapter_idx + 1}
                </span>
                {chapter.title && (
                  <span className="ml-2 text-zinc-500">— {chapter.title}</span>
                )}
              </div>
              <span
                className={`rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${
                  statusBadge[chapter.status] ?? statusBadge.uploaded
                }`}
              >
                {chapter.status}
              </span>
            </Link>
          ))}
        </div>
      </PageShell>
    );
  } catch {
    notFound();
  }
}
