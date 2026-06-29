from enum import Enum

from pydantic import AliasGenerator, BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class _RequestModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel)


class _ResponseModel(BaseModel):
    model_config = ConfigDict(alias_generator=AliasGenerator(serialization_alias=to_camel))


class PortalSpecimenInput(_RequestModel):
    label: str
    genotype: str | None = None


class PortalNeuronInput(_RequestModel):
    label: str
    specimen: PortalSpecimenInput


class PortalNodeInput(_RequestModel):
    index: int
    structure: int
    x: float
    y: float
    z: float
    radius: float
    parent_index: int
    atlas_structure: int | None = None


class ReconstructionInput(_RequestModel):
    id: str
    neuron: PortalNeuronInput
    nodes: list[PortalNodeInput]


class SkeletonRequest(_RequestModel):
    location: str
    # 0 is Neuroglancer's background segment, and segment ids are uint64.
    segment_id: int = Field(default=1, ge=1, le=2 ** 64 - 1)
    reconstruction: ReconstructionInput


class ErrorKind(str, Enum):
    INVALID_LOCATION = "InvalidLocation"
    PROTECTED_LOCATION = "ProtectedLocation"
    GENERATION_ERROR = "GenerationError"


class SkeletonResult(_ResponseModel):
    location: str
    segment_id: int
    node_count: int
    edge_count: int


class SkeletonResponse(_ResponseModel):
    service_version: str
    reconstruction_id: str
    result: SkeletonResult | None = None
    error_kind: ErrorKind | None = None
    error_description: str | None = None
    error_info: str | None = None
