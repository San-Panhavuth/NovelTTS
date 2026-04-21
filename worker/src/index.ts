import { Worker } from "bullmq";
import { Redis } from "ioredis";

const connection = new Redis(process.env.REDIS_URL ?? "redis://localhost:6379", {
  maxRetriesPerRequest: null,
});

const ttsWorker = new Worker(
  "tts-jobs",
  async (job) => {
    console.log(`[worker] processing job ${job.id} (${job.name})`);
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
