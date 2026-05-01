"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import {
  addBookPronunciation,
  apiDeleteWithAuth,
  apiGetWithAuth,
  apiPatchWithAuth,
  apiPostWithAuth,
  apiPutWithAuth,
  deleteBookPronunciation,
  inferBookPronunciations,
  updateBookPronunciation,
} from "@/lib/backend";

type ProcessChapterResult = {
  chapter_id: string;
  chapter_idx: number;
  status: string;
  segment_count: number;
};

export async function processChapter(formData: FormData) {
  const bookId = formData.get("bookId");
  const chapterIndex = formData.get("chapterIndex");

  if (typeof bookId !== "string" || typeof chapterIndex !== "string") {
    redirect("/library?message=Invalid chapter process request.");
  }

  let successMessage: string;
  try {
    const result = await apiPostWithAuth<ProcessChapterResult>(`/books/${bookId}/chapters/${chapterIndex}/process`);
    revalidatePath(`/books/${bookId}`);
    revalidatePath(`/books/${bookId}/chapters/${chapterIndex}`);
    successMessage = `Processed ${result.segment_count} segment(s).`;
  } catch (error) {
    const message = error instanceof Error ? error.message : "Processing failed.";
    redirect(`/books/${bookId}/chapters/${chapterIndex}?message=${encodeURIComponent(message)}`);
  }

  redirect(`/books/${bookId}/chapters/${chapterIndex}?message=${encodeURIComponent(successMessage)}`);
}

type UpdateSegmentResult = {
  id: string;
};

export async function updateSegmentCorrection(formData: FormData) {
  const bookId = formData.get("bookId");
  const chapterIndex = formData.get("chapterIndex");
  const segmentId = formData.get("segmentId");
  const type = formData.get("type");
  const characterName = formData.get("characterName");

  if (
    typeof bookId !== "string" ||
    typeof chapterIndex !== "string" ||
    typeof segmentId !== "string" ||
    typeof type !== "string"
  ) {
    redirect("/library?message=Invalid correction request.");
  }

  let successMessage = "Segment updated.";
  try {
    await apiPatchWithAuth<UpdateSegmentResult>(
      `/books/${bookId}/chapters/${chapterIndex}/segments/${segmentId}`,
      {
        type,
        character_name: typeof characterName === "string" ? characterName : null,
      }
    );
    revalidatePath(`/books/${bookId}/chapters/${chapterIndex}`);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Update failed.";
    redirect(`/books/${bookId}/chapters/${chapterIndex}?message=${encodeURIComponent(message)}`);
  }

  redirect(`/books/${bookId}/chapters/${chapterIndex}?message=${encodeURIComponent(successMessage)}`);
}

export type VoiceItem = {
  id: string;
  provider: string;
  provider_id: string;
  name: string;
  gender: string | null;
  locale: string | null;
  pitch: string | null;
  age_group: string | null;
  tone: string | null;
  energy: string | null;
  sample_url: string | null;
};

export type VoiceAssignmentData = {
  scope: string;
  narration_voice_id: string | null;
  dialogue_voice_id: string | null;
  thought_pitch_semitones: number;
};

export type ResolvedAssignmentData = {
  narration_voice_id: string | null;
  dialogue_voice_id: string | null;
  thought_pitch_semitones: number;
};

const VOICE_CACHE_TTL_MS = 5 * 60 * 1000;
let cachedVoices: VoiceItem[] | null = null;
let voicesCachedAt = 0;
let voicesInFlight: Promise<VoiceItem[]> | null = null;

export async function listVoices(): Promise<VoiceItem[]> {
  const now = Date.now();
  if (cachedVoices && now - voicesCachedAt < VOICE_CACHE_TTL_MS) {
    return cachedVoices;
  }

  if (!voicesInFlight) {
    voicesInFlight = (async () => {
      const voices = await apiGetWithAuth<VoiceItem[]>("/voices");

      // Preview endpoint uses Edge TTS, so keep only voices that are compatible.
      const previewableVoices = voices.filter(
        (voice) => voice.provider === "edge_tts" && voice.provider_id.includes("Neural")
      );

      const withPreviewFallback = previewableVoices.map((voice) => {
        if (voice.sample_url) return voice;
        return {
          ...voice,
          sample_url: `/api/voices/preview?voiceId=${encodeURIComponent(voice.provider_id)}`,
        };
      });

      cachedVoices = withPreviewFallback;
      voicesCachedAt = Date.now();
      return withPreviewFallback;
    })();
  }

  try {
    return await voicesInFlight;
  } finally {
    voicesInFlight = null;
  }
}

export async function getUserVoiceDefaults(): Promise<VoiceAssignmentData> {
  return apiGetWithAuth<VoiceAssignmentData>("/voice-settings/defaults");
}

export async function updateUserVoiceDefaults(
  narrationVoiceId: string | null,
  dialogueVoiceId: string | null,
  thoughtPitchSemitones: number
): Promise<VoiceAssignmentData> {
  return apiPutWithAuth<VoiceAssignmentData>("/voice-settings/defaults", {
    narration_voice_id: narrationVoiceId,
    dialogue_voice_id: dialogueVoiceId,
    thought_pitch_semitones: thoughtPitchSemitones,
  });
}

export async function getBookVoiceSettings(bookId: string): Promise<ResolvedAssignmentData> {
  return apiGetWithAuth<ResolvedAssignmentData>(`/books/${bookId}/voice-settings`);
}

export async function updateBookVoiceSettings(
  bookId: string,
  narrationVoiceId: string | null,
  dialogueVoiceId: string | null,
  thoughtPitchSemitones: number
): Promise<VoiceAssignmentData> {
  return apiPutWithAuth<VoiceAssignmentData>(`/books/${bookId}/voice-settings`, {
    narration_voice_id: narrationVoiceId,
    dialogue_voice_id: dialogueVoiceId,
    thought_pitch_semitones: thoughtPitchSemitones,
  });
}

// Server action wrappers for form submissions
export async function saveUserVoiceDefaults(formData: FormData) {
  const narrationVoiceId = formData.get("narrationVoiceId");
  const dialogueVoiceId = formData.get("dialogueVoiceId");
  const thoughtPitch = formData.get("thoughtPitchSemitones");

  let message = "Defaults saved.";
  try {
    await updateUserVoiceDefaults(
      typeof narrationVoiceId === "string" && narrationVoiceId ? narrationVoiceId : null,
      typeof dialogueVoiceId === "string" && dialogueVoiceId ? dialogueVoiceId : null,
      typeof thoughtPitch === "string" ? parseFloat(thoughtPitch) : -2.0
    );
    revalidatePath("/settings/voices");
  } catch (error) {
    message = error instanceof Error ? error.message : "Save failed.";
  }
  redirect(`/settings/voices?message=${encodeURIComponent(message)}`);
}

export async function saveBookVoiceSettings(formData: FormData) {
  const bookId = formData.get("bookId");
  const narrationVoiceId = formData.get("narrationVoiceId");
  const dialogueVoiceId = formData.get("dialogueVoiceId");
  const thoughtPitch = formData.get("thoughtPitchSemitones");

  if (typeof bookId !== "string") {
    redirect("/library?message=Invalid+book+id.");
  }

  let message = "Saved.";
  try {
    await updateBookVoiceSettings(
      bookId,
      typeof narrationVoiceId === "string" && narrationVoiceId ? narrationVoiceId : null,
      typeof dialogueVoiceId === "string" && dialogueVoiceId ? dialogueVoiceId : null,
      typeof thoughtPitch === "string" ? parseFloat(thoughtPitch) : -2.0
    );
    revalidatePath(`/books/${bookId}/voice-settings`);
  } catch (error) {
    message = error instanceof Error ? error.message : "Save failed.";
  }
  redirect(`/books/${bookId}/voice-settings?message=${encodeURIComponent(message)}`);
}

export async function inferBookPronunciationDictionary(formData: FormData) {
  const bookId = formData.get("bookId");

  if (typeof bookId !== "string") {
    redirect("/library?message=Invalid pronunciation request.");
  }

  let message = "Pronunciation inference complete.";
  try {
    const result = await inferBookPronunciations(bookId);
    revalidatePath(`/books/${bookId}/pronunciations`);
    message = `Inferred ${result.inference_metadata.unique_terms} pronunciation${
      result.inference_metadata.unique_terms === 1 ? "" : "s"
    } from ${result.inference_metadata.segments_processed} segment${
      result.inference_metadata.segments_processed === 1 ? "" : "s"
    }.`;
  } catch (error) {
    message = error instanceof Error ? error.message : "Inference failed.";
  }

  redirect(`/books/${bookId}/pronunciations?message=${encodeURIComponent(message)}`);
}

export async function createBookPronunciation(formData: FormData) {
  const bookId = formData.get("bookId");
  const term = formData.get("term");
  const phoneme = formData.get("phoneme");
  const languageCode = formData.get("languageCode");

  if (typeof bookId !== "string" || typeof term !== "string" || typeof phoneme !== "string") {
    redirect("/library?message=Invalid pronunciation request.");
  }

  let message = "Pronunciation saved.";
  try {
    await addBookPronunciation(bookId, {
      term,
      phoneme,
      language_code: typeof languageCode === "string" && languageCode ? languageCode : null,
    });
    revalidatePath(`/books/${bookId}/pronunciations`);
  } catch (error) {
    message = error instanceof Error ? error.message : "Save failed.";
  }

  redirect(`/books/${bookId}/pronunciations?message=${encodeURIComponent(message)}`);
}

export async function updateBookPronunciationEntry(formData: FormData) {
  const bookId = formData.get("bookId");
  const entryId = formData.get("entryId");
  const term = formData.get("term");
  const phoneme = formData.get("phoneme");
  const languageCode = formData.get("languageCode");

  if (
    typeof bookId !== "string" ||
    typeof entryId !== "string" ||
    typeof term !== "string" ||
    typeof phoneme !== "string"
  ) {
    redirect("/library?message=Invalid pronunciation update.");
  }

  let message = "Pronunciation updated.";
  try {
    await updateBookPronunciation(bookId, entryId, {
      term,
      phoneme,
      language_code: typeof languageCode === "string" && languageCode ? languageCode : null,
    });
    revalidatePath(`/books/${bookId}/pronunciations`);
  } catch (error) {
    message = error instanceof Error ? error.message : "Update failed.";
  }

  redirect(`/books/${bookId}/pronunciations?message=${encodeURIComponent(message)}`);
}

export async function deleteBook(formData: FormData) {
  const bookId = formData.get("bookId");

  if (typeof bookId !== "string") {
    redirect("/library?message=Invalid+book+id.");
  }

  try {
    await apiDeleteWithAuth<{ success: boolean }>(`/books/${bookId}`);
    revalidatePath("/library");
  } catch (error) {
    const message = error instanceof Error ? error.message : "Delete failed.";
    redirect(`/books/${bookId}?message=${encodeURIComponent(message)}`);
  }

  redirect("/library");
}

export async function deleteBookPronunciationEntry(formData: FormData) {
  const bookId = formData.get("bookId");
  const entryId = formData.get("entryId");

  if (typeof bookId !== "string" || typeof entryId !== "string") {
    redirect("/library?message=Invalid pronunciation delete request.");
  }

  let message = "Pronunciation deleted.";
  try {
    await deleteBookPronunciation(bookId, entryId);
    revalidatePath(`/books/${bookId}/pronunciations`);
  } catch (error) {
    message = error instanceof Error ? error.message : "Delete failed.";
  }

  redirect(`/books/${bookId}/pronunciations?message=${encodeURIComponent(message)}`);
}
