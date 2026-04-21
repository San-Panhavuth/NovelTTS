import { redirect } from "next/navigation";
import {
  createSupabaseServerClient,
  getSupabaseMissingConfigMessage,
  isSupabaseConfigured,
} from "@/lib/supabase";

export default async function Home() {
  if (!isSupabaseConfigured()) {
    return (
      <main className="mx-auto flex min-h-screen w-full max-w-3xl flex-col gap-8 px-6 py-12">
        <section className="space-y-2">
          <h1 className="text-3xl font-semibold tracking-tight">NovelTTS</h1>
          <p className="text-sm text-zinc-600 dark:text-zinc-400">
            Supabase auth is not configured yet.
          </p>
        </section>
        <section className="space-y-3 rounded-lg border p-4">
          <h2 className="text-lg font-medium">Setup required</h2>
          <p className="text-sm">{getSupabaseMissingConfigMessage()}</p>
        </section>
      </main>
    );
  }

  const supabase = await createSupabaseServerClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/login");
  }

  redirect("/library");
}
