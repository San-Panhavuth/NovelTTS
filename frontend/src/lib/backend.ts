import { createSupabaseServerClient } from "@/lib/supabase";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const REQUEST_TIMEOUT_MS = 8000;

function candidateBaseUrls(): string[] {
  const urls = [API_BASE_URL];

  if (API_BASE_URL.includes("localhost")) {
    urls.push(API_BASE_URL.replace("localhost", "127.0.0.1"));
  } else if (API_BASE_URL.includes("127.0.0.1")) {
    urls.push(API_BASE_URL.replace("127.0.0.1", "localhost"));
  }

  return [...new Set(urls)];
}

async function getAccessToken() {
  const supabase = await createSupabaseServerClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  return session?.access_token ?? null;
}

async function buildApiError(prefix: string, response: Response): Promise<Error> {
  let detail = `${prefix}: ${response.status}`;

  try {
    const contentType = response.headers.get("content-type") ?? "";
    if (contentType.includes("application/json")) {
      const payload = (await response.json()) as { detail?: string };
      if (payload?.detail) {
        detail = `${prefix}: ${response.status} (${payload.detail})`;
      }
    } else {
      const text = await response.text();
      if (text) {
        detail = `${prefix}: ${response.status} (${text.slice(0, 300)})`;
      }
    }
  } catch {
    // Keep fallback status-only error if body parsing fails.
  }

  return new Error(detail);
}

export async function apiGetWithAuth<T>(path: string): Promise<T> {
  const token = await getAccessToken();
  if (!token) {
    throw new Error("Missing access token");
  }

  let response: Response | null = null;
  for (const baseUrl of candidateBaseUrls()) {
    try {
      response = await fetch(`${baseUrl}${path}`, {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        cache: "no-store",
        signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
      });
      break;
    } catch {
      response = null;
    }
  }

  if (!response) {
    throw new Error(`Backend is unreachable. Make sure the FastAPI service is running on ${API_BASE_URL}.`);
  }

  if (!response.ok) {
    throw await buildApiError("API request failed", response);
  }

  return (await response.json()) as T;
}

export async function apiPostWithAuth<T>(path: string, body?: unknown): Promise<T> {
  const token = await getAccessToken();
  if (!token) {
    throw new Error("Missing access token");
  }

  let response: Response | null = null;
  for (const baseUrl of candidateBaseUrls()) {
    try {
      response = await fetch(`${baseUrl}${path}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: body === undefined ? undefined : JSON.stringify(body),
        cache: "no-store",
        signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
      });
      break;
    } catch {
      response = null;
    }
  }

  if (!response) {
    throw new Error(`Backend is unreachable. Make sure the FastAPI service is running on ${API_BASE_URL}.`);
  }

  if (!response.ok) {
    throw await buildApiError("API request failed", response);
  }

  return (await response.json()) as T;
}

export async function apiPatchWithAuth<T>(path: string, body: unknown): Promise<T> {
  const token = await getAccessToken();
  if (!token) {
    throw new Error("Missing access token");
  }

  let response: Response | null = null;
  for (const baseUrl of candidateBaseUrls()) {
    try {
      response = await fetch(`${baseUrl}${path}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(body),
        cache: "no-store",
        signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
      });
      break;
    } catch {
      response = null;
    }
  }

  if (!response) {
    throw new Error(`Backend is unreachable. Make sure the FastAPI service is running on ${API_BASE_URL}.`);
  }

  if (!response.ok) {
    throw await buildApiError("API request failed", response);
  }

  return (await response.json()) as T;
}

export async function apiPutWithAuth<T>(path: string, body: unknown): Promise<T> {
  const token = await getAccessToken();
  if (!token) {
    throw new Error("Missing access token");
  }

  let response: Response | null = null;
  for (const baseUrl of candidateBaseUrls()) {
    try {
      response = await fetch(`${baseUrl}${path}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(body),
        cache: "no-store",
        signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
      });
      break;
    } catch {
      response = null;
    }
  }

  if (!response) {
    throw new Error(`Backend is unreachable. Make sure the FastAPI service is running on ${API_BASE_URL}.`);
  }

  if (!response.ok) {
    throw await buildApiError("API request failed", response);
  }

  return (await response.json()) as T;
}

export async function apiDeleteWithAuth<T>(path: string): Promise<T> {
  const token = await getAccessToken();
  if (!token) {
    throw new Error("Missing access token");
  }

  let response: Response | null = null;
  for (const baseUrl of candidateBaseUrls()) {
    try {
      response = await fetch(`${baseUrl}${path}`, {
        method: "DELETE",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        cache: "no-store",
        signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
      });
      break;
    } catch {
      response = null;
    }
  }

  if (!response) {
    throw new Error(`Backend is unreachable. Make sure the FastAPI service is running on ${API_BASE_URL}.`);
  }

  if (!response.ok) {
    throw await buildApiError("API request failed", response);
  }

  return (await response.json()) as T;
}

export async function apiUploadWithAuth<T>(path: string, formData: FormData): Promise<T> {
  const token = await getAccessToken();
  if (!token) {
    throw new Error("Missing access token");
  }

  let response: Response | null = null;
  for (const baseUrl of candidateBaseUrls()) {
    try {
      response = await fetch(`${baseUrl}${path}`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
        cache: "no-store",
        signal: AbortSignal.timeout(REQUEST_TIMEOUT_MS),
      });
      break;
    } catch {
      response = null;
    }
  }

  if (!response) {
    throw new Error(`Backend is unreachable. Make sure the FastAPI service is running on ${API_BASE_URL}.`);
  }

  if (!response.ok) {
    throw await buildApiError("Upload failed", response);
  }

  return (await response.json()) as T;
}

export type PronunciationEntry = {
  id: string;
  term: string;
  phoneme: string;
  language_code: string | null;
  created_at: string | null;
  updated_at: string | null;
};

export type PronunciationListResponse = {
  entries: PronunciationEntry[];
  total: number;
};

export type PronunciationInferenceResponse = {
  entries: PronunciationEntry[];
  inference_metadata: {
    total_segments: number;
    segments_processed: number;
    unique_terms: number;
  };
};

export async function getBookPronunciations(bookId: string): Promise<PronunciationListResponse> {
  return apiGetWithAuth<PronunciationListResponse>(`/books/${bookId}/pronunciations`);
}

export async function inferBookPronunciations(bookId: string): Promise<PronunciationInferenceResponse> {
  return apiPostWithAuth<PronunciationInferenceResponse>(`/books/${bookId}/pronunciations/infer`);
}

export async function addBookPronunciation(
  bookId: string,
  payload: { term: string; phoneme: string; language_code?: string | null }
): Promise<PronunciationEntry> {
  return apiPostWithAuth<PronunciationEntry>(`/books/${bookId}/pronunciations`, payload);
}

export async function updateBookPronunciation(
  bookId: string,
  entryId: string,
  payload: { term?: string; phoneme?: string; language_code?: string | null }
): Promise<PronunciationEntry> {
  return apiPutWithAuth<PronunciationEntry>(`/books/${bookId}/pronunciations/${entryId}`, payload);
}

export async function deleteBookPronunciation(bookId: string, entryId: string): Promise<{ success: boolean }> {
  return apiDeleteWithAuth<{ success: boolean }>(`/books/${bookId}/pronunciations/${entryId}`);
}
