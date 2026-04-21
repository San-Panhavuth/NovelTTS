from enum import StrEnum


class SegmentType(StrEnum):
    NARRATION = "narration"
    DIALOGUE = "dialogue"
    THOUGHT = "thought"


class JobStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
