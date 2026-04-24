"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { apiGetWithAuth, apiPatchWithAuth, apiPostWithAuth, apiPutWithAuth } from "@/lib/backend";

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

export async function listVoices(): Promise<VoiceItem[]> {
  return apiGetWithAuth<VoiceItem[]>("/voices");
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

  try {
    await updateUserVoiceDefaults(
      typeof narrationVoiceId === "string" && narrationVoiceId ? narrationVoiceId : null,
      typeof dialogueVoiceId === "string" && dialogueVoiceId ? dialogueVoiceId : null,
      typeof thoughtPitch === "string" ? parseFloat(thoughtPitch) : -2.0
    );
    revalidatePath("/settings/voices");
    redirect("/settings/voices?message=Defaults+saved.");
  } catch (error) {
    const message = error instanceof Error ? error.message : "Save failed.";
    redirect(`/settings/voices?message=${encodeURIComponent(message)}`);
  }
}

export async function saveBookVoiceSettings(formData: FormData) {
  const bookId = formData.get("bookId");
  const narrationVoiceId = formData.get("narrationVoiceId");
  const dialogueVoiceId = formData.get("dialogueVoiceId");
  const thoughtPitch = formData.get("thoughtPitchSemitones");

  if (typeof bookId !== "string") {
    redirect("/library?message=Invalid+book+id.");
  }

  try {
    await updateBookVoiceSettings(
      bookId,
      typeof narrationVoiceId === "string" && narrationVoiceId ? narrationVoiceId : null,
      typeof dialogueVoiceId === "string" && dialogueVoiceId ? dialogueVoiceId : null,
      typeof thoughtPitch === "string" ? parseFloat(thoughtPitch) : -2.0
    );
    revalidatePath(`/books/${bookId}/voice-settings`);
    redirect(`/books/${bookId}/voice-settings?message=Saved.`);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Save failed.";
    redirect(`/books/${bookId}/voice-settings?message=${encodeURIComponent(message)}`);
  }
}
