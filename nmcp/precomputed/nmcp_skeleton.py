from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional, Self, List

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

    @classmethod
    def create(cls, nodes: List[dict]):
        skeleton = cls()
        skeleton.append(nodes)
        return skeleton

    def append(self, nodes: List[dict]):
        """
        Add segment data to the skeleton.  This is presumed to be a continuation of existing skeleton part such as
        axon chunks being accumulated.  See `concat` for merging axon and dendrite parts with adjustment for both
        containing a soma reference.
        """
        if nodes is None or len(nodes) == 0:
            return

        df = pd.DataFrame(nodes)

        vertices = df[["x", "y", "z"]].values

        edges = df[["sampleNumber", "parentNumber"]].values[1:] - 1

        radii = df["radius"].values.astype(np.float32)

        if df.allenId.isna().all():
            df["allenId"] = 0
        else:
            # fill all the na values with 0
            df["allenId"] = df["allenId"].fillna(0)

        ccf_ids = df["allenId"].values.astype(np.float32)

        compartments = df["structureIdentifier"].values.astype(np.float32)

        self.vertices = np.concatenate([self.vertices, vertices])
        self.edges = np.concatenate([self.edges, edges])
        self.radii = np.concatenate([self.radii, radii])
        self.ccf_ids = np.concatenate([self.ccf_ids, ccf_ids])
        self.compartments = np.concatenate([self.compartments, compartments])

    def concat(self, other: Self) -> Self:
        # Assumed to be an axon with dendrite in that order.
        if not isinstance(other, SkeletonComponents):
            raise TypeError("can only concatenate SkeletonComponents")

        # Get the current number of vertices to adjust edge indices
        existing_vertex_count = len(self.vertices)

        # Adjust new edges to reference correct vertex indices
        adjusted_edges = other.edges + existing_vertex_count - 1

        if len(self.vertices) > 0 and len(other.edges) > 0:
            # Map any dendrite edges that would have referenced the soma in the dendrite structure
            # to the axon soma vertex.
            adjusted_edges[adjusted_edges[:, 1] == self.vertices.shape[0] - 1, 1] = 0

        return SkeletonComponents(
            vertices=np.concatenate([self.vertices, other.vertices[1:]]),
            edges=np.concatenate([self.edges, adjusted_edges]),
            radii=np.concatenate([self.radii, other.radii[1:]]),
            ccf_ids=np.concatenate([self.ccf_ids, other.ccf_ids[1:]]),
            compartments=np.concatenate([self.compartments, other.compartments[1:]])
        )


def create_skeleton_components(data: dict) -> tuple[SkeletonComponents | None, SkeletonComponents | None]:
    axon = None
    dendrite = None

    if data["axon"]:
        axon = SkeletonComponents.create(data["axon"])

    if data["dendrite"]:
        dendrite = SkeletonComponents.create(data["dendrite"])

    return axon, dendrite


def create_skeleton(skeleton_id: int, axon: SkeletonComponents, dendrite: SkeletonComponents) -> Skeleton:
    if axon is None:
        assert dendrite is not None
        output = dendrite
    elif dendrite is None:
        assert axon is not None
        output = axon
    else:
        output = axon.concat(dendrite)

    sk = Skeleton(segid=skeleton_id)

    sk.vertices = output.vertices
    sk.edges = output.edges
    sk.radii = output.radii
    sk.extra_attributes = vertex_attributes

    sk.radius = output.radii
    sk.allenId = output.ccf_ids
    sk.compartment = output.compartments

    return sk
