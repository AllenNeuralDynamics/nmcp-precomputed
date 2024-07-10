from dataclasses import dataclass


@dataclass
class PrecomputedEntry:
    id: str
    skeletonSegmentId: int
    version: int | None
    reconstructionId: str
    generatedAt: float | None
