import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { PageShell } from "@/app/components/page-shell";
import { PitchSlider } from "@/app/components/pitch-slider";
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
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) redirect("/login");

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
    <PageShell
      title="Voice Settings"
      subtitle={`${book.title} · Overrides your global defaults for this book`}
      maxWidth="md"
      breadcrumbs={[
        { label: "Library", href: "/library" },
        { label: book.title, href: `/books/${id}` },
        { label: "Voice Settings" },
      ]}
    >
      {message && (
        <div className="mb-4 rounded-lg bg-zinc-100 px-4 py-2.5 text-sm dark:bg-zinc-800">
          {decodeURIComponent(message)}
        </div>
      )}

      <form action={saveBookVoiceSettings} className="space-y-4">
        <input type="hidden" name="bookId" value={id} />

        {/* Narration card */}
        <div className="rounded-2xl border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-900">
          <div className="mb-4 space-y-0.5">
            <h2 className="text-sm font-semibold">Narration Voice</h2>
            <p className="text-xs text-zinc-500 dark:text-zinc-400">
              Used for all non-dialogue, non-thought lines. Leave empty to inherit your global default.
            </p>
          </div>
          <VoicePicker
            label=""
            name="narrationVoiceId"
            voices={voices}
            defaultValue={normalizeVoiceValue(resolved.narration_voice_id, voices)}
            placeholder="(inherits from default)"
          />
        </div>

        {/* Dialogue card */}
        <div className="rounded-2xl border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-900">
          <div className="mb-4 space-y-0.5">
            <h2 className="text-sm font-semibold">Dialogue Voice</h2>
            <p className="text-xs text-zinc-500 dark:text-zinc-400">
              Used for spoken dialogue. Also applies to thought lines with the pitch offset below.
            </p>
          </div>
          <VoicePicker
            label=""
            name="dialogueVoiceId"
            voices={voices}
            defaultValue={normalizeVoiceValue(resolved.dialogue_voice_id, voices)}
            placeholder="(inherits from default)"
          />
        </div>

        {/* Thought pitch card */}
        <div className="rounded-2xl border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-900">
          <div className="mb-4 space-y-0.5">
            <h2 className="text-sm font-semibold">Thought Pitch Offset</h2>
            <p className="text-xs text-zinc-500 dark:text-zinc-400">
              Shifts the dialogue voice pitch for inner-thought segments. Negative = lower, softer feel.
            </p>
          </div>
          <PitchSlider defaultValue={resolved.thought_pitch_semitones} />
        </div>

        <div className="flex items-center justify-between pt-2">
          <Link href="/settings/voices" className="text-sm text-zinc-500 hover:underline">
            Edit global defaults →
          </Link>
          <button
            type="submit"
            className="rounded-lg bg-zinc-900 px-6 py-2 text-sm font-medium text-white hover:bg-zinc-700 dark:bg-zinc-100 dark:text-zinc-900 dark:hover:bg-zinc-300"
          >
            Save Settings
          </button>
        </div>
      </form>
    </PageShell>
  );
}
