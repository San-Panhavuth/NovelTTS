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
    throw new Error(
      "Backend is unreachable. Make sure the FastAPI service is running on localhost:8000."
    );
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
    throw new Error(
      "Backend is unreachable. Make sure the FastAPI service is running on localhost:8000."
    );
  }

  if (!response.ok) {
    throw await buildApiError("Upload failed", response);
  }

  return (await response.json()) as T;
}
