import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import {
  researchCharacterProfiles,
  researchVoiceRequirements,
} from "@/app/books/actions";
import { SignOutForm } from "@/app/components/sign-out-form";
import { apiGetWithAuth } from "@/lib/backend";
import {
  createSupabaseServerClient,
  isSupabaseConfigured,
} from "@/lib/supabase";

type VoiceRecommendation = {
  voice_id: string;
  voice_name: string;
  provider: string;
  score: number;
  rationale: string;
};

type CharacterProfile = {
  age: string | null;
  gender: string | null;
  personality: string[];
  speech_style: string[];
  role: string | null;
  voice_notes: string | null;
  confidence: number | null;
};

type VoiceRequirement = {
  pitch: string | null;
  age_group: string | null;
  tone: string | null;
  pacing: string | null;
  energy: string | null;
  avoid: string[];
  rationale: string | null;
};

type CharacterVoiceCard = {
  character_id: string;
  character_name: string;
  assigned_voice_id: string | null;
  profile: CharacterProfile | null;
  requirement: VoiceRequirement | null;
  recommendations: VoiceRecommendation[];
};

type VoiceDashboard = {
  book_id: string;
  items: CharacterVoiceCard[];
};

type VoiceDashboardPageProps = {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ message?: string }>;
};

export default async function VoiceDashboardPage({
  params,
  searchParams,
}: VoiceDashboardPageProps) {
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

  try {
    const dashboard = await apiGetWithAuth<VoiceDashboard>(`/books/${id}/voices/dashboard`);
    return (
      <main className="mx-auto flex min-h-screen w-full max-w-6xl flex-col gap-6 px-6 py-10">
        <section className="flex items-start justify-between gap-4">
          <div className="space-y-2">
            <h1 className="text-3xl font-semibold tracking-tight">
              Voice Dashboard
            </h1>
            <p className="text-sm text-zinc-600 dark:text-zinc-400">
              Character profiles, generated voice requirements, and top voice
              recommendations.
            </p>
          </div>
          <SignOutForm />
        </section>

        {message ? <p className="rounded-md border px-3 py-2 text-sm">{message}</p> : null}

        <section className="flex flex-wrap gap-3">
          <form action={researchCharacterProfiles}>
            <input type="hidden" name="bookId" value={id} />
            <button className="rounded-md border px-4 py-2 text-sm">
              Re-research Profiles
            </button>
          </form>
          <form action={researchVoiceRequirements}>
            <input type="hidden" name="bookId" value={id} />
            <button className="rounded-md border px-4 py-2 text-sm">
              Generate Voice Requirements
            </button>
          </form>
          <Link href={`/books/${id}`} className="rounded-md border px-4 py-2 text-sm">
            Back to Book
          </Link>
        </section>

        <section className="grid gap-4">
          {dashboard.items.length === 0 ? (
            <p className="rounded-md border p-4 text-sm">
              No characters found yet. Process chapters first in Phase 2.
            </p>
          ) : (
            dashboard.items.map((item) => (
              <article key={item.character_id} className="rounded-lg border p-4">
                <h2 className="text-lg font-semibold">{item.character_name}</h2>
                <p className="mt-1 text-xs text-zinc-600 dark:text-zinc-400">
                  Assigned voice: {item.assigned_voice_id ?? "none"}
                </p>

                <div className="mt-3 grid gap-3 md:grid-cols-2">
                  <div className="rounded-md border p-3 text-sm">
                    <p className="font-medium">Profile</p>
                    {!item.profile ? (
                      <p className="mt-1 text-zinc-600 dark:text-zinc-400">
                        Not generated yet.
                      </p>
                    ) : (
                      <div className="mt-2 space-y-1 text-xs">
                        <p>Role: {item.profile.role ?? "n/a"}</p>
                        <p>Age: {item.profile.age ?? "n/a"}</p>
                        <p>Gender: {item.profile.gender ?? "n/a"}</p>
                        <p>Confidence: {item.profile.confidence?.toFixed(2) ?? "n/a"}</p>
                        <p>
                          Personality:{" "}
                          {item.profile.personality.length > 0
                            ? item.profile.personality.join(", ")
                            : "n/a"}
                        </p>
                        <p>
                          Speech style:{" "}
                          {item.profile.speech_style.length > 0
                            ? item.profile.speech_style.join(", ")
                            : "n/a"}
                        </p>
                      </div>
                    )}
                  </div>

                  <div className="rounded-md border p-3 text-sm">
                    <p className="font-medium">Voice Requirement</p>
                    {!item.requirement ? (
                      <p className="mt-1 text-zinc-600 dark:text-zinc-400">
                        Not generated yet.
                      </p>
                    ) : (
                      <div className="mt-2 space-y-1 text-xs">
                        <p>Pitch: {item.requirement.pitch ?? "n/a"}</p>
                        <p>Age group: {item.requirement.age_group ?? "n/a"}</p>
                        <p>Tone: {item.requirement.tone ?? "n/a"}</p>
                        <p>Pacing: {item.requirement.pacing ?? "n/a"}</p>
                        <p>Energy: {item.requirement.energy ?? "n/a"}</p>
                        <p>
                          Avoid:{" "}
                          {item.requirement.avoid.length > 0
                            ? item.requirement.avoid.join(", ")
                            : "none"}
                        </p>
                      </div>
                    )}
                  </div>
                </div>

                <div className="mt-3 rounded-md border p-3 text-sm">
                  <p className="font-medium">Top Recommendations</p>
                  {item.recommendations.length === 0 ? (
                    <p className="mt-1 text-zinc-600 dark:text-zinc-400">
                      No recommendations available. Add voices and requirements first.
                    </p>
                  ) : (
                    <ul className="mt-2 space-y-1 text-xs">
                      {item.recommendations.map((rec) => (
                        <li key={rec.voice_id}>
                          {rec.voice_name} ({rec.provider}) - score {rec.score} - {rec.rationale}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </article>
            ))
          )}
        </section>
      </main>
    );
  } catch {
    notFound();
  }
}
