"use client";

import { useCallback, useEffect, useRef, useState } from "react";

type JobStatus = "idle" | "queued" | "processing" | "completed" | "failed";

type AudioPlayerProps = {
  bookId: string;
  chapterIdx: string;
  initialOutputUrl?: string | null;
  initialJobId?: string | null;
};

function resolveAudioSrc(outputUrl: string): string {
  if (outputUrl.startsWith("r2://")) {
    const key = outputUrl.slice("r2://".length).replace(/^\/+/, "");
    return `/api/audio/${key}`;
  }
  // Backward compatibility for early jobs that stored a relative key-like path.
  if (outputUrl.startsWith("/audio/")) {
    return `/api${outputUrl}`;
  }
  // If a non-public R2 endpoint URL was stored, proxy by key path.
  try {
    const parsed = new URL(outputUrl);
    const match = parsed.pathname.match(/\/(audio\/.+\.mp3)$/i);
    if (match?.[1]) {
      return `/api/audio/${match[1]}`;
    }
  } catch {
    // Ignore parse failures and return URL as-is.
  }
  return outputUrl;
}

export function AudioPlayer({ bookId, chapterIdx, initialOutputUrl, initialJobId }: AudioPlayerProps) {
  const [status, setStatus] = useState<JobStatus>(
    initialOutputUrl ? "completed" : initialJobId ? "queued" : "idle"
  );
  const [progress, setProgress] = useState(0);
  const [outputUrl, setOutputUrl] = useState<string | null>(initialOutputUrl ?? null);
  const [error, setError] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(initialJobId ?? null);
  const [generating, setGenerating] = useState(false);
  const [pollFailures, setPollFailures] = useState(0);
  const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const poll = useCallback(async (id: string) => {
    try {
      const res = await fetch(`/api/jobs/${id}`);
      if (!res.ok) {
        const payload = (await res.json().catch(() => null)) as { detail?: string } | null;
        const retries = pollFailures + 1;
        setPollFailures(retries);
        if (retries >= 5) {
          setStatus("failed");
          setError(payload?.detail ?? "Lost job status updates. Please retry generation.");
          return;
        }
        pollRef.current = setTimeout(() => poll(id), 2500);
        return;
      }
      setPollFailures(0);
      const data = await res.json() as {
        status: string; progress: number; output_url: string | null; error: string | null
      };
      setProgress(data.progress);
      if (data.status === "processing") setStatus("processing");
      if (data.status === "queued") setStatus("queued");
      if (data.status === "completed") {
        setStatus("completed");
        setOutputUrl(data.output_url);
      } else if (data.status === "failed") {
        setStatus("failed");
        setError(data.error ?? "Generation failed");
      } else {
        pollRef.current = setTimeout(() => poll(id), 2000);
      }
    } catch {
      const retries = pollFailures + 1;
      setPollFailures(retries);
      if (retries >= 5) {
        setStatus("failed");
        setError("Network error while polling job status. Backend may be restarting.");
        return;
      }
      pollRef.current = setTimeout(() => poll(id), 3000);
    }
  }, [pollFailures]);

  useEffect(() => {
    if (jobId && (status === "queued" || status === "processing")) {
      poll(jobId);
    }
    return () => { if (pollRef.current) clearTimeout(pollRef.current); };
  }, [jobId, status, poll]);

  async function handleGenerate() {
    if (pollRef.current) clearTimeout(pollRef.current);
    setGenerating(true);
    setError(null);
    setStatus("queued");
    setProgress(0);
    setPollFailures(0);
    try {
      const res = await fetch(`/api/generate/${bookId}/${chapterIdx}`, { method: "POST" });
      const data = await res.json() as { job_id?: string; detail?: string };
      if (!res.ok) {
        setStatus("failed");
        setError(data.detail ?? "Failed to start generation");
        return;
      }
      setJobId(data.job_id!);
      poll(data.job_id!);
    } catch {
      setStatus("failed");
      setError("Network error while starting generation.");
    } finally {
      setGenerating(false);
    }
  }

  return (
    <div className="rounded-xl border border-zinc-200 bg-white p-5 dark:border-zinc-800 dark:bg-zinc-900">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold">Audio</h3>
        <button
          onClick={handleGenerate}
          disabled={generating || status === "queued" || status === "processing"}
          className="rounded-lg bg-indigo-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {status === "queued" || status === "processing"
            ? "Generating…"
            : status === "completed"
              ? "Regenerate Audio"
              : "Generate Audio"}
        </button>
      </div>

      {(status === "queued" || status === "processing") && (
        <div className="space-y-1.5">
          <div className="h-2 w-full overflow-hidden rounded-full bg-zinc-100 dark:bg-zinc-800">
            <div
              className="h-full rounded-full bg-indigo-500 transition-all duration-500"
              style={{ width: `${Math.max(progress, 4)}%` }}
            />
          </div>
          <p className="text-xs text-zinc-500">
            {status === "queued" ? "Queued…" : `Synthesizing… ${progress}%`}
          </p>
        </div>
      )}

      {status === "failed" && (
        <div className="space-y-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-900 dark:bg-red-950 dark:text-red-300">
          <p>{error}</p>
          <button
            onClick={handleGenerate}
            className="rounded-md border border-red-300 px-2 py-1 text-xs hover:bg-red-100 dark:border-red-700 dark:hover:bg-red-900"
          >
            Retry generation
          </button>
        </div>
      )}

      {status === "completed" && outputUrl && !outputUrl.startsWith("local://") && (
        <audio controls className="w-full" src={resolveAudioSrc(outputUrl)}>
          Your browser does not support audio.
        </audio>
      )}

      {status === "completed" && outputUrl?.startsWith("local://") && (
        <p className="text-xs text-zinc-500">
          Generated locally (R2 not configured). File saved at:{" "}
          <code className="font-mono">{outputUrl.replace("local://", "")}</code>
        </p>
      )}

      {status === "idle" && (
        <p className="text-xs text-zinc-400">
          Process the chapter first, then generate audio.
        </p>
      )}
    </div>
  );
}
