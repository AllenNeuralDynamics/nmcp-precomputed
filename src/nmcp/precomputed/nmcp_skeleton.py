import copy

from typing_extensions import List

import numpy as np
import pandas as pd

from cloudvolume import Skeleton

from .neuron_structure import NeuronStructure
from ..data.portal_reconstruction import PortalNode

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


class SkeletonComponents:
    def __init__(self, nodes: List[PortalNode], structure: NeuronStructure | None = None):
        if nodes is None or len(nodes) == 0:
            self.vertices: np.ndarray = np.empty((0, 3), dtype=np.float32)
            self.edges: np.ndarray = np.empty((0, 2), dtype=np.float32)
            self.radii: np.ndarray = np.empty(0, dtype=np.float32)
            self.atlas_structure_ids: np.ndarray = np.empty(0, dtype=np.float32)
            self.node_structure_ids: np.ndarray = np.empty(0, dtype=np.float32)
            return

        nodes = SkeletonComponents.select_nodes(nodes, structure)

        df = pd.DataFrame(nodes)

        vertices = df[["x", "y", "z"]].values

        edges = df[["index", "parentIndex"]].values[1:]

        radii = df["radius"].values.astype(np.float32)

        if "atlasStructure" in df.columns:
            if df["atlasStructure"].isna().all():
                df["atlasStructure"] = 0
            else:
                # fill all the na values with 0
                df["atlasStructure"] = df["atlasStructure"].fillna(0)

            ccf_ids = df["atlasStructure"].values.astype(np.float32)
        else:
            ccf_ids = np.full(len(nodes), 0, dtype=np.float32)

        structure_ids = df["structure"].values.astype(np.float32)

        self.vertices = vertices
        self.edges = edges
        self.radii = radii
        self.atlas_structure_ids = ccf_ids
        self.node_structure_ids = structure_ids

    def create_skeleton(self, skeleton_id: int) -> Skeleton:
        sk = Skeleton(segid=skeleton_id)

        sk.vertices = self.vertices
        sk.edges = self.edges
        sk.radii = self.radii
        sk.extra_attributes = vertex_attributes

        sk.radius = self.radii
        sk.allenId = self.atlas_structure_ids
        sk.compartment = self.node_structure_ids

        return sk

    @staticmethod
    def select_nodes(src_nodes: List[PortalNode], structure: NeuronStructure | None) -> List[PortalNode]:
        # May be modifying indices.
        nodes = copy.deepcopy(src_nodes)

        if structure is not None:
            node_ids = [(node["index"], node["parentIndex"]) for node in nodes if node["structure"] == structure]

            flat_map = [item for tup in node_ids for item in tup]

            unique = list(set(flat_map))

            # All nodes including the parent of the first node of this structure type.  Parent typically would be the soma
            # but could be from the other structure (e.g., axon from dendrite).
            required_nodes = [node for node in nodes if node["index"] in unique]

            # Find that root node whose parent is not expected to be in the final list, either because it doesn't exist
            # (soma) or would mean including parts of the other structure beyond just where the junction occurs (axon
            # from dendrite case).
            root = next((node for node in required_nodes if node["parentIndex"] not in node_ids))
        else:
            required_nodes = nodes
            root = next((node for node in required_nodes if node["parentIndex"] == -1))

        node_map = {root["parentIndex"]: -1}

        # Remap indices to contiguous [0...N] for skeleton which required that edges index into a vertices array with
        # that property.  This is for situations like substructures that start at an offset within the total node list
        # skips indices in the original SWC/source, or indices not starting at 0 even for the full structure (e.g., SWC
        # starting at 1).
        for idx, node in enumerate(required_nodes):
            node_map[node["index"]] = idx
            node["index"] = idx

        for node in required_nodes:
            node["parentIndex"] = node_map[node["parentIndex"]]

        return required_nodes
