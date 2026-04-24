"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { apiPatchWithAuth, apiPostWithAuth } from "@/lib/backend";

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
