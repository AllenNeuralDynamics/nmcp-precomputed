import json
import pickle
from typing import List

from cloudvolume import CloudVolume
from cloudfiles import CloudFiles

from .nmcp_skeleton import create_skeleton, vertex_attributes
from .segment_info import SegmentInfo


def create_from_json(json_files: [], cloud_location: str):
    neurons = list()

    for json_file in json_files:
        with open(json_file) as f:
            data = json.load(f)
            neurons.append(data["neurons"][0])

    create_from_dict(neurons, cloud_location)


def create_from_dict(neurons: List[dict], cloud_location: str) -> List[int]:
    cv = create_dataset_info(cloud_location)

    skeletons = list()

    cf = CloudFiles(cloud_location)

    existing = cf.get("segment_properties/info.pickle")

    if existing is not None:
        segment_properties = pickle.loads(existing)
    else:
        segment_properties = SegmentInfo()

    ids = list()

    for neuron in neurons:
        skeleton_id = None
        if "skeletonId" in neuron:
            skeleton_id = neuron["skeletonId"]
        elif "idString" in neuron:
            try:
                skeleton_id = int(neuron["idString"][1:4])
            except:
                pass

        if skeleton_id is not None:
            skeletons.append(load_from_dict(skeleton_id, neuron, segment_properties))
            ids.append(skeleton_id)

    cv.skeleton.upload(skeletons)

    create_segment_properties(cloud_location, segment_properties)

    return ids


def load_from_dict(skeleton_id: int, data: dict, segment_properties: SegmentInfo):
    sk = create_skeleton(skeleton_id, data)
    extract_segment_properties(data, sk.id, segment_properties)
    return sk


def create_dataset_info(cloud_location: str) -> CloudVolume:
    """ Once per dataset """
    info = CloudVolume.create_new_info(
        num_channels=1,
        layer_type="segmentation",
        data_type="uint64",  # Channel images might be "uint8"
        # raw, png, jpeg, compressed_segmentation, fpzip, compressed, zfpc, compresso, crackle
        encoding="raw",
        resolution=[1000, 1000, 1000],  # Voxel scaling, units are in nanometers
        voxel_offset=[0, 0, 0],  # x,y,z offset in voxels from the origin
        # mesh="mesh",
        skeletons="skeleton",
        # Pick a convenient size for your underlying chunk representation
        # Powers of two are recommended, doesn't need to cover image exactly
        chunk_size=[512, 512, 512],  # units are voxels
        volume_size=[13200, 8000, 11400],  # e.g. a cubic millimeter dataset
    )

    info["segment_properties"] = "segment_properties"

    cv = CloudVolume(f"precomputed://{cloud_location}", info=info, compress=False)

    sk_info = cv.skeleton.meta.default_info()

    sk_info["transform"] = [1000, 0, 0, 0, 0, 1000, 0, 0, 0, 0, 1000, 0]
    sk_info["vertex_attributes"] = vertex_attributes
    cv.skeleton.meta.info = sk_info
    cv.skeleton.meta.commit_info()

    cv.commit_info()

    return cv


def extract_segment_properties(data: dict, segment_id: int, segment_properties: SegmentInfo):
    soma_allen_id = data["soma"]["allenId"]

    label = (data["idString"])

    sample = data["sample"]
    if sample is not None and sample["strain"] is not None:
        strain = sample["strain"]
    else:
        strain = "unknown"

    segment_properties.append(segment_id, label, strain, soma_allen_id)


def create_segment_properties(cloud_location: str, segment_properties: SegmentInfo):
    """ Once per dataset"""

    cf = CloudFiles(cloud_location)
    cf.put_json("segment_properties/info", segment_properties.as_dict())
    cf.put("segment_properties/info.pickle", pickle.dumps(segment_properties))
