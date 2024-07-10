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


def create_segment(axon_df: pd.DataFrame, offset: int = 0, edge_offset: int = 0):
    if len(axon_df) > 0:
        axon_vertices = axon_df[['x', 'y', 'z']].values[offset:]
        axon_edges = axon_df[['sampleNumber', 'parentNumber']].values[1:] - 1 + edge_offset
        axon_radius = axon_df['radius'].values[offset:].astype(np.float32)
        if axon_df.allenId.isna().all():
            axon_df['allenId'] = 0
        else:
            # fill all the na values with 0
            axon_df['allenId'] = axon_df['allenId'].fillna(0)
        axon_ccf_id = axon_df['allenId'].values.astype(np.float32)[offset:]
        axon_compartment = axon_df['structureIdentifier'].values.astype(np.float32)[offset:]

        return axon_vertices, axon_edges, axon_radius, axon_ccf_id, axon_compartment

    empty = np.empty(0, dtype=np.float32)

    return empty, empty, empty, empty, empty


def create_skeleton(skeleton_id: int, data: dict) -> Skeleton:
    axon_vertices, axon_edges, axon_radius, axon_ccf_id, axon_compartment = create_segment(pd.DataFrame(data["axon"]))

    dend_vertices, dend_edges, dend_radius, dend_ccf_id, dend_compartment = create_segment(
        pd.DataFrame(data["dendrite"]), 1, -1 + axon_vertices.shape[0])

    if len(axon_vertices) > 0 and len(dend_edges) > 0:
        dend_edges[dend_edges[:, 1] == axon_vertices.shape[0] - 1, 1] = 0

    vertices = np.concatenate([axon_vertices, dend_vertices])
    edges = np.concatenate([axon_edges, dend_edges])
    radius = np.concatenate([axon_radius, dend_radius])
    ccf_id = np.concatenate([axon_ccf_id, dend_ccf_id])
    compartment = np.concatenate([axon_compartment, dend_compartment])

    sk = Skeleton(
        vertices=vertices,
        edges=edges,
        radii=radius,
        # segid=int(data['idString'][1:4]),
        segid=skeleton_id,
        extra_attributes=vertex_attributes
    )
    sk.radius = radius
    sk.allenId = ccf_id
    sk.compartment = compartment

    assert (len(sk.allenId) == len(sk.vertices))
    assert (len(sk.radius) == len(sk.vertices))
    assert (len(sk.compartment) == len(sk.vertices))

    return sk
