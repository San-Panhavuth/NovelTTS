import { Worker } from "bullmq";
import { Redis } from "ioredis";

const queueName = process.env.AUDIO_GENERATION_QUEUE_NAME ?? "audio-generation";
const backendUrl = process.env.BACKEND_INTERNAL_URL ?? "http://localhost:8010";
const workerSecret = process.env.WORKER_SHARED_SECRET ?? "dev-worker-secret";

const connection = new Redis(process.env.REDIS_URL ?? "redis://localhost:6379", {
  maxRetriesPerRequest: null,
});

const ttsWorker = new Worker(
  queueName,
  async (job) => {
    console.log(`[worker] processing job ${job.id} (${job.name})`);

    const response = await fetch(`${backendUrl}/internal/worker/audio-generate`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Worker-Secret": workerSecret,
      },
      body: JSON.stringify(job.data),
    });

    if (!response.ok) {
      const body = await response.text();
      throw new Error(`backend worker endpoint failed (${response.status}): ${body}`);
    }

    return { ok: true };
  },
  { connection }
);

ttsWorker.on("completed", (job) => {
  console.log(`[worker] completed job ${job?.id}`);
});

ttsWorker.on("failed", (job, error) => {
  console.error(`[worker] failed job ${job?.id}`, error);
});

process.on("SIGINT", async () => {
  await ttsWorker.close();
  await connection.quit();
  process.exit(0);
});

console.log("[worker] BullMQ worker started");
