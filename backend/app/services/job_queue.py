from __future__ import annotations

import logging

from bullmq import Queue

from app.config import settings

logger = logging.getLogger(__name__)


async def enqueue_audio_generation_job(job_id: str, user_id: str) -> None:
    queue = Queue(
        settings.audio_generation_queue_name,
        {"connection": settings.redis_url},
    )
    try:
        await queue.add(
            "audio.generate",
            {
                "job_id": job_id,
                "user_id": user_id,
            },
            {"jobId": job_id},
        )
        logger.info("queue: enqueued audio generation job=%s", job_id)
    finally:
        await queue.close()
