from dataclasses import dataclass


@dataclass
class PrecomputedEntry:
    id: str
    skeletonId: int
    version: int | None
    reconstructionId: str
    generatedAt: float | None
