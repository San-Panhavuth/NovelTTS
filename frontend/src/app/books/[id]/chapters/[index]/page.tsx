import Link from "next/link";
import { notFound, redirect } from "next/navigation";
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

type ChapterPageProps = {
  params: Promise<{ id: string; index: string }>;
};

export default async function ChapterPage({ params }: ChapterPageProps) {
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

  try {
    const chapter = await apiGetWithAuth<ChapterDetail>(`/books/${id}/chapters/${index}`);
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

        <article className="whitespace-pre-wrap rounded-lg border p-4 text-sm leading-7">
          {chapter.raw_text}
        </article>

        <Link href={`/books/${id}`} className="text-sm underline">
          Back to book
        </Link>
      </main>
    );
  } catch {
    notFound();
  }
}
