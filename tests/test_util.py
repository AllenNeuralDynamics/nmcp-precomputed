import json
import os
import pickle
from pathlib import Path

from cloudvolume import CloudVolume

from nmcp.data.portal_reconstruction import PortalReconstruction


def verify_precomputed_file(location: str, skeleton_id: int, node_count: int):
    skeleton_dir = os.path.join(location, "skeleton")
    assert os.path.isdir(skeleton_dir)

    segment_properties_dir = os.path.join(location, "segment_properties")
    assert os.path.isdir(segment_properties_dir)

    info_file = os.path.join(location, "info")
    assert os.path.isfile(info_file)

    pickle_file = os.path.join(segment_properties_dir, "info.pickle")
    assert os.path.isfile(pickle_file)

    with open(pickle_file, "rb") as input_file:
        s = pickle.loads(input_file.read())

    assert s is not None

    if skeleton_id is not None:
        cf = CloudVolume(location)

        skel = cf.skeleton.get(skeleton_id)

        assert skel is not None

        if node_count is not None:
            assert skel.vertices.shape == (node_count, 3)


def load_reconstruction(name: str = "portalFormatSmall.json") -> PortalReconstruction:
    with open(Path(__file__).parent.joinpath("fixtures").joinpath(name)) as f:
        return json.load(f)
