import { notFound, redirect } from "next/navigation";
import Link from "next/link";
import { PageShell } from "@/app/components/page-shell";
import { AudioPlayer } from "@/app/components/audio-player";
import { ChapterTabs } from "@/app/components/chapter-tabs";
import { FlashMessage } from "@/app/components/flash_message";
import { processChapter } from "@/app/books/actions";
import { createSupabaseServerClient, isSupabaseConfigured } from "@/lib/supabase";
import { apiGetWithAuth } from "@/lib/backend";

type ChapterDetail = {
  id: string;
  chapter_idx: number;
  title: string | null;
  status: string;
  raw_text: string;
};

type Segment = {
  id: string;
  segment_idx: number;
  text: string;
  type: "narration" | "dialogue" | "thought";
  character_id: string | null;
  character_name: string | null;
  confidence: number | null;
  low_confidence: boolean;
};

type JobStatus = {
  job_id: string;
  status: string;
  progress: number;
  error: string | null;
  output_url: string | null;
};

type ChapterPageProps = {
  params: Promise<{ id: string; index: string }>;
  searchParams: Promise<{ message?: string }>;
};

export default async function ChapterPage({ params, searchParams }: ChapterPageProps) {
  if (!isSupabaseConfigured()) redirect("/login?message=Supabase env is not configured.");

  const supabase = await createSupabaseServerClient();
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect("/login");

  const { id, index } = await params;
  const { message } = await searchParams;

  try {
    const [chapter, segments, latestJob] = await Promise.all([
      apiGetWithAuth<ChapterDetail>(`/books/${id}/chapters/${index}`),
      apiGetWithAuth<Segment[]>(`/books/${id}/chapters/${index}/segments`).catch(() => []),
      apiGetWithAuth<JobStatus>(`/books/${id}/chapters/${index}/latest-job`).catch(() => null),
    ]);

    const chapterLabel = `Chapter ${chapter.chapter_idx + 1}`;
    const needsReview = (segments as Segment[]).filter((s) => s.low_confidence).length;

    return (
      <PageShell
        title={chapterLabel}
        subtitle={`${chapter.status}${needsReview > 0 ? ` · ${needsReview} need${needsReview > 1 ? "" : "s"} review` : ""}`}
        maxWidth="xl"
        breadcrumbs={[
          { label: "Library", href: "/library" },
          { label: "Book", href: `/books/${id}` },
          { label: chapterLabel },
        ]}
        actions={
          <div className="flex gap-2">
            <Link
              href={`/books/${id}/pronunciations`}
              className="rounded-lg border border-zinc-200 px-3 py-1.5 text-sm hover:bg-zinc-50 dark:border-zinc-700 dark:hover:bg-zinc-800"
            >
              Pronunciations
            </Link>
            <form action={processChapter}>
              <input type="hidden" name="bookId" value={id} />
              <input type="hidden" name="chapterIndex" value={index} />
              {chapter.status === "uploaded" ? (
                <button
                  type="submit"
                  className="rounded-lg bg-indigo-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-indigo-700"
                >
                  Process chapter
                </button>
              ) : (
                <button
                  type="submit"
                  className="rounded-lg border border-zinc-200 px-3 py-1.5 text-sm hover:bg-zinc-50 dark:border-zinc-700 dark:hover:bg-zinc-800"
                >
                  ↻ Re-process
                </button>
              )}
            </form>
          </div>
        }
      >
        {message && <FlashMessage variant="warning" />}

        {/* Audio player — only shown after chapter has been processed */}
        {chapter.status !== "uploaded" && (
          <div className="mb-6">
            <AudioPlayer
              bookId={id}
              chapterIdx={index}
              initialOutputUrl={latestJob?.output_url}
              initialJobId={
                latestJob && latestJob.status !== "completed" && latestJob.status !== "failed"
                  ? latestJob.job_id
                  : null
              }
            />
          </div>
        )}

        {/* Raw Text / Segments tabs */}
        <ChapterTabs
          rawText={chapter.raw_text}
          segments={segments as Segment[]}
          bookId={id}
          chapterIndex={index}
        />
      </PageShell>
    );
  } catch {
    notFound();
  }
}
