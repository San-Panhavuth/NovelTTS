import { notFound, redirect } from "next/navigation";
import Link from "next/link";
import { PageShell } from "@/app/components/page-shell";
import { AudioPlayer } from "@/app/components/audio-player";
import { FlashMessage } from "@/app/components/flash_message";
import { processChapter, updateSegmentCorrection } from "@/app/books/actions";
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

const typeStyles: Record<string, { pill: string; border: string }> = {
  narration: {
    pill: "bg-blue-50 text-blue-700 dark:bg-blue-950 dark:text-blue-300",
    border: "border-l-blue-400",
  },
  dialogue: {
    pill: "bg-amber-50 text-amber-700 dark:bg-amber-950 dark:text-amber-300",
    border: "border-l-amber-400",
  },
  thought: {
    pill: "bg-violet-50 text-violet-700 dark:bg-violet-950 dark:text-violet-300",
    border: "border-l-violet-400",
  },
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

    const chapterLabel = `Chapter ${chapter.chapter_idx + 1}${chapter.title ? `: ${chapter.title}` : ""}`;
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
            <form action={processChapter} className="flex gap-2">
              <input type="hidden" name="bookId" value={id} />
              <input type="hidden" name="chapterIndex" value={index} />
              <button
                type="submit"
                className="rounded-lg border border-zinc-200 px-3 py-1.5 text-sm hover:bg-zinc-50 dark:border-zinc-700 dark:hover:bg-zinc-800"
              >
                ↻ Re-process
              </button>
            </form>
          </div>
        }
      >
        {message && <FlashMessage variant="warning" />}

        {/* Audio player */}
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

        {/* Segments */}
        {(segments as Segment[]).length === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-2xl border-2 border-dashed border-zinc-200 py-16 text-center dark:border-zinc-800">
            <p className="text-sm font-medium text-zinc-500">No segments yet</p>
            <p className="mt-1 text-xs text-zinc-400">Click Re-process to run attribution</p>
          </div>
        ) : (
          <div className="space-y-2">
            <div className="mb-4 flex flex-wrap items-center gap-3 text-xs">
              {(["narration", "dialogue", "thought"] as const).map((t) => (
                <span key={t} className={`rounded-full px-2.5 py-0.5 font-medium ${typeStyles[t].pill}`}>
                  {t}
                </span>
              ))}
              <span className="ml-2 text-zinc-400">{(segments as Segment[]).length} segments</span>
            </div>

            {(segments as Segment[]).map((segment) => {
              const styles = typeStyles[segment.type] ?? typeStyles.narration;
              return (
                <div
                  key={segment.id}
                  className={`rounded-xl border border-zinc-200 border-l-4 bg-white dark:border-zinc-800 dark:bg-zinc-900 ${styles.border} ${
                    segment.low_confidence ? "ring-1 ring-amber-300 dark:ring-amber-700" : ""
                  }`}
                >
                  <div className="flex items-center gap-2 border-b border-zinc-100 px-4 py-2 dark:border-zinc-800">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${styles.pill}`}>
                      {segment.type}
                    </span>
                    {segment.character_name && (
                      <span className="text-xs text-zinc-500">{segment.character_name}</span>
                    )}
                    <span className="ml-auto text-xs text-zinc-400">
                      #{segment.segment_idx + 1}
                      {segment.confidence !== null && <> · {(segment.confidence * 100).toFixed(0)}%</>}
                      {segment.low_confidence && <span className="ml-1 text-amber-500">⚠ review</span>}
                    </span>
                  </div>

                  <p className="px-4 py-3 text-sm leading-7 text-zinc-800 dark:text-zinc-200">
                    {segment.text}
                  </p>

                  <form
                    action={updateSegmentCorrection}
                    className="flex flex-wrap items-center gap-2 border-t border-zinc-100 px-4 py-2.5 dark:border-zinc-800"
                  >
                    <input type="hidden" name="bookId" value={id} />
                    <input type="hidden" name="chapterIndex" value={index} />
                    <input type="hidden" name="segmentId" value={segment.id} />

                    <select
                      name="type"
                      defaultValue={segment.type}
                      className="rounded-md border border-zinc-200 bg-transparent px-2 py-1 text-xs focus:outline-none dark:border-zinc-700"
                    >
                      <option value="narration">narration</option>
                      <option value="dialogue">dialogue</option>
                      <option value="thought">thought</option>
                    </select>

                    <input
                      type="text"
                      name="characterName"
                      defaultValue={segment.character_name ?? ""}
                      placeholder="Character (optional)"
                      className="min-w-40 rounded-md border border-zinc-200 bg-transparent px-2 py-1 text-xs placeholder-zinc-400 focus:outline-none dark:border-zinc-700"
                    />

                    <button
                      type="submit"
                      className="rounded-md bg-zinc-900 px-3 py-1 text-xs text-white hover:bg-zinc-700 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300"
                    >
                      Save
                    </button>
                  </form>
                </div>
              );
            })}
          </div>
        )}
      </PageShell>
    );
  } catch {
    notFound();
  }
}
