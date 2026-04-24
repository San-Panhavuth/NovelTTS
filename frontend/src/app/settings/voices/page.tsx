import Link from "next/link";
import { redirect } from "next/navigation";
import { SignOutForm } from "@/app/components/sign-out-form";
import { PitchSlider } from "@/app/components/pitch-slider";
import { VoicePicker } from "@/app/components/voice-picker";
import { createSupabaseServerClient, isSupabaseConfigured } from "@/lib/supabase";
import { getUserVoiceDefaults, listVoices, saveUserVoiceDefaults } from "@/app/books/actions";

type VoiceDefaultsPageProps = {
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
          defaultValue={normalizeVoiceValue(defaults.narration_voice_id, voices)}
          placeholder="(none)"
        />

        <VoicePicker
          label="Dialogue Voice"
          description="Also used for thought segments with the pitch offset applied below."
          name="dialogueVoiceId"
          voices={voices}
          defaultValue={normalizeVoiceValue(defaults.dialogue_voice_id, voices)}
          placeholder="(none)"
        />

        <PitchSlider defaultValue={defaults.thought_pitch_semitones} />

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
