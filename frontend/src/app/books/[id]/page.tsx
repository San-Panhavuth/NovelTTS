import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { SignOutForm } from "@/app/components/sign-out-form";
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

export default async function BookDetailPage({ params }: BookDetailPageProps) {
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

  const { id } = await params;

  try {
    const book = await apiGetWithAuth<BookDetail>(`/books/${id}`);

    return (
      <main className="mx-auto flex min-h-screen w-full max-w-5xl flex-col gap-6 px-6 py-10">
        <section className="flex items-start justify-between gap-4">
          <div className="space-y-2">
            <h1 className="text-3xl font-semibold tracking-tight">{book.title}</h1>
            <p className="text-sm text-zinc-600 dark:text-zinc-400">
              {book.author || "Unknown author"} · {book.origin_language || "Unknown language"}
            </p>
          </div>
          <SignOutForm />
        </section>

        <section className="space-y-3">
          {book.chapters.map((chapter) => (
            <Link
              key={chapter.id}
              href={`/books/${book.id}/chapters/${chapter.chapter_idx}`}
              className="block rounded-lg border p-4 hover:bg-zinc-50 dark:hover:bg-zinc-900"
            >
              <h2 className="text-lg font-medium">
                Chapter {chapter.chapter_idx + 1}: {chapter.title || "Untitled"}
              </h2>
              <p className="text-sm text-zinc-600 dark:text-zinc-400">Status: {chapter.status}</p>
            </Link>
          ))}
        </section>

        <div>
          <button className="rounded-md border px-4 py-2 text-sm" disabled>
            Process (Phase 2)
          </button>
        </div>
      </main>
    );
  } catch {
    notFound();
  }
}
