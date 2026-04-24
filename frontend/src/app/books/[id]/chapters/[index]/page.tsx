import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { processChapter, updateSegmentCorrection } from "@/app/books/actions";
import { SignOutForm } from "@/app/components/sign-out-form";
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

type ChapterPageProps = {
  params: Promise<{ id: string; index: string }>;
  searchParams: Promise<{ message?: string }>;
};

export default async function ChapterPage({ params, searchParams }: ChapterPageProps) {
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

  const { id, index } = await params;
  const { message } = await searchParams;

  try {
    const chapter = await apiGetWithAuth<ChapterDetail>(`/books/${id}/chapters/${index}`);
    let segments: Segment[] = [];
    try {
      segments = await apiGetWithAuth<Segment[]>(`/books/${id}/chapters/${index}/segments`);
    } catch {
      segments = [];
    }

    return (
      <main className="mx-auto flex min-h-screen w-full max-w-5xl flex-col gap-6 px-6 py-10">
        <section className="flex items-start justify-between gap-4">
          <div className="space-y-2">
            <h1 className="text-3xl font-semibold tracking-tight">
              Chapter {chapter.chapter_idx + 1}: {chapter.title || "Untitled"}
            </h1>
            <p className="text-sm text-zinc-600 dark:text-zinc-400">Status: {chapter.status}</p>
          </div>
          <SignOutForm />
        </section>

        {message ? <p className="rounded-md border px-3 py-2 text-sm">{message}</p> : null}

        <form action={processChapter}>
          <input type="hidden" name="bookId" value={id} />
          <input type="hidden" name="chapterIndex" value={index} />
          <button className="rounded-md border px-4 py-2 text-sm">Process Chapter</button>
        </form>

        <article className="whitespace-pre-wrap rounded-lg border p-4 text-sm leading-7">
          {chapter.raw_text}
        </article>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold tracking-tight">Attributed Segments</h2>
          {segments.length === 0 ? (
            <p className="rounded-lg border p-4 text-sm text-zinc-600 dark:text-zinc-400">
              No segments yet. Click "Process Chapter" to generate attribution output.
            </p>
          ) : (
            segments.map((segment) => (
              <article
                key={segment.id}
                className={`rounded-lg border p-4 text-sm ${
                  segment.low_confidence ? "border-amber-400 bg-amber-50/50" : ""
                }`}
              >
                <p className="mb-2 text-xs text-zinc-600 dark:text-zinc-400">
                  #{segment.segment_idx + 1} · {segment.type}
                  {segment.character_name ? ` · ${segment.character_name}` : ""} · confidence: {" "}
                  {segment.confidence === null ? "n/a" : segment.confidence.toFixed(2)}
                  {segment.low_confidence ? " · needs review" : ""}
                </p>
                <p className="whitespace-pre-wrap leading-7">{segment.text}</p>
                <form action={updateSegmentCorrection} className="mt-4 flex flex-wrap items-end gap-2">
                  <input type="hidden" name="bookId" value={id} />
                  <input type="hidden" name="chapterIndex" value={index} />
                  <input type="hidden" name="segmentId" value={segment.id} />

                  <label className="text-xs">
                    Type
                    <select
                      name="type"
                      defaultValue={segment.type}
                      className="ml-2 rounded-md border px-2 py-1 text-xs"
                    >
                      <option value="narration">narration</option>
                      <option value="dialogue">dialogue</option>
                      <option value="thought">thought</option>
                    </select>
                  </label>

                  <label className="text-xs">
                    Character
                    <input
                      type="text"
                      name="characterName"
                      defaultValue={segment.character_name ?? ""}
                      placeholder="Leave blank for none"
                      className="ml-2 min-w-52 rounded-md border px-2 py-1 text-xs"
                    />
                  </label>

                  <button className="rounded-md border px-3 py-1 text-xs">Save correction</button>
                </form>
              </article>
            ))
          )}
        </section>

        <Link href={`/books/${id}`} className="text-sm underline">
          Back to book
        </Link>
      </main>
    );
  } catch {
    notFound();
  }
}
