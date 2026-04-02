from typing import TypedDict, List


class PortalNode(TypedDict):
    index: int
    structure: int
    x: float
    y: float
    z: float
    radius: float
    parentIndex: int
    atlasStructure: int


class PortalSpecimen(TypedDict):
    date: float | None
    label: str
    genotype: str | None


class PortalNeuron(TypedDict):
    label: str
    specimen: PortalSpecimen


class PortalReconstruction(TypedDict):
    id: str
    neuron: PortalNeuron
    nodes: List[PortalNode]
