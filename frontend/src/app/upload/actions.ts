"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { apiUploadWithAuth } from "@/lib/backend";

type UploadResponse = {
  id: string;
};

export async function uploadEpub(formData: FormData) {
  const file = formData.get("file");
  if (!(file instanceof File)) {
    redirect("/upload?message=Please select an EPUB file.");
  }

  const payload = new FormData();
  payload.append("file", file);

  let uploaded: UploadResponse;
  try {
    uploaded = await apiUploadWithAuth<UploadResponse>("/books/upload", payload);
  } catch (error) {
    const message = error instanceof Error ? error.message : "Upload failed.";
    redirect(`/upload?message=${encodeURIComponent(message)}`);
  }

  revalidatePath("/library");
  redirect(`/books/${uploaded.id}`);
}
