import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { PitchSlider } from "@/app/components/pitch-slider";
import { SignOutForm } from "@/app/components/sign-out-form";
import { VoicePicker } from "@/app/components/voice-picker";
import { createSupabaseServerClient, isSupabaseConfigured } from "@/lib/supabase";
import { getBookVoiceSettings, listVoices, saveBookVoiceSettings } from "@/app/books/actions";
import { apiGetWithAuth } from "@/lib/backend";

type BookDetail = {
  id: string;
  title: string;
};

type VoiceSettingsPageProps = {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ message?: string }>;
};

function normalizeVoiceValue(raw: string | null, voices: { id: string; provider_id: string }[]): string {
  if (!raw) return "";
  const byProvider = voices.find((v) => v.provider_id === raw);
  if (byProvider) return byProvider.provider_id;
  const byId = voices.find((v) => v.id === raw);
  if (byId) return byId.provider_id;
  return "";
}

export default async function BookVoiceSettingsPage({ params, searchParams }: VoiceSettingsPageProps) {
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
  const { message } = await searchParams;

  let book: BookDetail;
  try {
    book = await apiGetWithAuth<BookDetail>(`/books/${id}`);
  } catch {
    notFound();
  }

  const [voices, resolved] = await Promise.all([
    listVoices().catch(() => []),
    getBookVoiceSettings(id).catch(() => ({
      narration_voice_id: null,
      dialogue_voice_id: null,
      thought_pitch_semitones: -2.0,
    })),
  ]);

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-3xl flex-col gap-6 px-6 py-10">
      <section className="flex items-start justify-between gap-4">
        <div className="space-y-1">
          <Link href={`/books/${id}`} className="text-sm text-zinc-500 hover:underline">
            ← {book.title}
          </Link>
          <h1 className="text-2xl font-semibold tracking-tight">Voice Settings</h1>
          <p className="text-sm text-zinc-600 dark:text-zinc-400">
            Override voices for this book. Empty fields fall back to your global defaults.
          </p>
        </div>
        <SignOutForm />
      </section>

      {message && (
        <p className="rounded-md bg-zinc-100 px-4 py-2 text-sm dark:bg-zinc-800">
          {decodeURIComponent(message)}
        </p>
      )}

      <form action={saveBookVoiceSettings} className="flex flex-col gap-6">
        <input type="hidden" name="bookId" value={id} />

        <VoicePicker
          label="Narration Voice"
          name="narrationVoiceId"
          voices={voices}
          defaultValue={normalizeVoiceValue(resolved.narration_voice_id, voices)}
          placeholder="(inherits from default)"
        />

        <VoicePicker
          label="Dialogue Voice"
          description="Also used for thought segments with the pitch offset applied below."
          name="dialogueVoiceId"
          voices={voices}
          defaultValue={normalizeVoiceValue(resolved.dialogue_voice_id, voices)}
          placeholder="(inherits from default)"
        />

        <PitchSlider defaultValue={resolved.thought_pitch_semitones} />

        <button
          type="submit"
          className="self-start rounded-md bg-zinc-900 px-6 py-2 text-sm text-white hover:bg-zinc-700 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300"
        >
          Save
        </button>
      </form>

      <div className="mt-4">
        <Link href="/settings/voices" className="text-sm text-zinc-500 hover:underline">
          Edit global voice defaults →
        </Link>
      </div>
    </main>
  );
}
