from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional, Self

import numpy as np
import pandas as pd

from cloudvolume import Skeleton

vertex_attributes = [
    {
        'id': 'radius',
        'data_type': 'float32',
        'num_components': 1
    },
    {
        "id": "allenId",
        "data_type": "float32",
        "num_components": 1

    },
    {
        "id": "compartment",
        "data_type": "float32",
        "num_components": 1
    }
]


class ReconstructionType(IntEnum):
    AXON = 0
    DENDRITE = 1
    ALL = 2


_NP_EMPTY = np.empty(0, dtype=np.float32)
_NP_EMPTY_VERTEX = np.empty((0, 3), dtype=np.float32)
_NP_EMPTY_EDGE = np.empty((0, 2), dtype=np.float32)


@dataclass
class SkeletonComponents:
    vertices: np.ndarray = field(default_factory=lambda: _NP_EMPTY_VERTEX)
    edges: np.ndarray = field(default_factory=lambda: _NP_EMPTY_EDGE)
    radii: np.ndarray = field(default_factory=lambda: _NP_EMPTY)
    ccf_ids: np.ndarray = field(default_factory=lambda: _NP_EMPTY)
    compartments: np.ndarray = field(default_factory=lambda: _NP_EMPTY)

    def concat(self, other: Self) -> Self:
        if not isinstance(other, SkeletonComponents):
            raise TypeError("can only concatenate SkeletonComponents")

        return SkeletonComponents(
            vertices=np.concatenate([self.vertices, other.vertices]),
            edges=np.concatenate([self.edges, other.edges]),
            radii=np.concatenate([self.radii, other.radii]),
            ccf_ids=np.concatenate([self.ccf_ids, other.ccf_ids]),
            compartments=np.concatenate([self.compartments, other.compartments])
        )


def create_segment(df: pd.DataFrame, offset: int = 0, edge_offset: int = 0) -> Optional[SkeletonComponents]:
    components = SkeletonComponents()

    if len(df) == 0:
        return components

    components.vertices = df[["x", "y", "z"]].values[offset:]

    components.edges = df[["sampleNumber", "parentNumber"]].values[1:] - 1 + edge_offset

    components.radii = df["radius"].values[offset:].astype(np.float32)

    if df.allenId.isna().all():
        df["allenId"] = 0
    else:
        # fill all the na values with 0
        df["allenId"] = df["allenId"].fillna(0)

    components.ccf_ids = df["allenId"].values.astype(np.float32)[offset:]

    components.compartments = df["structureIdentifier"].values.astype(np.float32)[offset:]

    return components


def create_skeleton(skeleton_id: int, data: dict, reconstruction_type: ReconstructionType) -> Skeleton:
    if reconstruction_type == ReconstructionType.AXON or reconstruction_type == ReconstructionType.ALL:
        axon_components = create_segment(pd.DataFrame(data["axon"]))
        # If loading dendrite next, a) skip the soma which would be a duplicate, and b) adjust the vertex references
        # in dendrite edges to account for the axon vertices already loaded and the removed soma.
        offset = (1, axon_components.vertices.shape[0] - 1)
    else:
        axon_components = SkeletonComponents()
        offset = (0, 0)

    if reconstruction_type == ReconstructionType.DENDRITE or reconstruction_type == ReconstructionType.ALL:
        dendrite_components = create_segment(pd.DataFrame(data["dendrite"]), *offset)
    else:
        dendrite_components = SkeletonComponents()

    if len(axon_components.vertices) > 0 and len(dendrite_components.edges) > 0:
        # Map any dendrite edges that would have referenced the soma in the dendrite structure to the axon soma vertex.
        dendrite_components.edges[dendrite_components.edges[:, 1] == axon_components.vertices.shape[0] - 1, 1] = 0

    output = axon_components.concat(dendrite_components)

    sk = Skeleton(
        vertices=output.vertices,
        edges=output.edges,
        radii=output.radii,
        segid=skeleton_id,
        extra_attributes=vertex_attributes
    )

    sk.radius = output.radii
    sk.allenId = output.ccf_ids
    sk.compartment = output.compartments

    assert (len(sk.allenId) == len(sk.vertices))
    assert (len(sk.radius) == len(sk.vertices))
    assert (len(sk.compartment) == len(sk.vertices))

    return sk
