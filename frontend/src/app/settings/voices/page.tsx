import Link from "next/link";
import { redirect } from "next/navigation";
import { SignOutForm } from "@/app/components/sign-out-form";
import { VoicePicker } from "@/app/components/voice-picker";
import { createSupabaseServerClient, isSupabaseConfigured } from "@/lib/supabase";
import { getUserVoiceDefaults, listVoices, saveUserVoiceDefaults } from "@/app/books/actions";

type VoiceDefaultsPageProps = {
  searchParams: Promise<{ message?: string }>;
};

export default async function UserVoiceDefaultsPage({ searchParams }: VoiceDefaultsPageProps) {
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

  const { message } = await searchParams;

  const [voices, defaults] = await Promise.all([
    listVoices().catch(() => []),
    getUserVoiceDefaults().catch(() => ({
      scope: "user",
      narration_voice_id: null,
      dialogue_voice_id: null,
      thought_pitch_semitones: -2.0,
    })),
  ]);

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-3xl flex-col gap-6 px-6 py-10">
      <section className="flex items-start justify-between gap-4">
        <div className="space-y-1">
          <Link href="/library" className="text-sm text-zinc-500 hover:underline">
            ← Library
          </Link>
          <h1 className="text-2xl font-semibold tracking-tight">Global Voice Defaults</h1>
          <p className="text-sm text-zinc-600 dark:text-zinc-400">
            Applied to all books unless overridden per book.
          </p>
        </div>
        <SignOutForm />
      </section>

      {message && (
        <p className="rounded-md bg-zinc-100 px-4 py-2 text-sm dark:bg-zinc-800">
          {decodeURIComponent(message)}
        </p>
      )}

      <form action={saveUserVoiceDefaults} className="flex flex-col gap-6">
        <VoicePicker
          label="Narration Voice"
          name="narrationVoiceId"
          voices={voices}
          defaultValue={defaults.narration_voice_id ?? ""}
          placeholder="(none)"
        />

        <VoicePicker
          label="Dialogue Voice"
          description="Also used for thought segments with the pitch offset applied below."
          name="dialogueVoiceId"
          voices={voices}
          defaultValue={defaults.dialogue_voice_id ?? ""}
          placeholder="(none)"
        />

        <div className="flex flex-col gap-2">
          <label htmlFor="thoughtPitch" className="text-sm font-medium">
            Thought Pitch Offset (semitones)
          </label>
          <p className="text-xs text-zinc-500">
            Applied to the dialogue voice for inner-monologue segments. Default: −2 st.
          </p>
          <input
            id="thoughtPitch"
            type="range"
            name="thoughtPitchSemitones"
            min="-12"
            max="0"
            step="0.5"
            defaultValue={defaults.thought_pitch_semitones}
            className="w-full"
          />
          <span className="text-xs text-zinc-500">
            Current: {defaults.thought_pitch_semitones} st
          </span>
        </div>

        <button
          type="submit"
          className="self-start rounded-md bg-zinc-900 px-6 py-2 text-sm text-white hover:bg-zinc-700 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300"
        >
          Save defaults
        </button>
      </form>
    </main>
  );
}
