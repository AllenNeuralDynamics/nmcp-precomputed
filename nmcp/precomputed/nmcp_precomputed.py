import json
import logging
import pickle
from typing import List

from cloudvolume import CloudVolume
from cloudfiles import CloudFiles
from osteoid import Skeleton

from .nmcp_skeleton import create_skeleton, vertex_attributes, ReconstructionType
from .segment_info import SegmentInfo, NmcpPropertyValues

logger = logging.getLogger(__name__)


def create_from_json(json_files: [], cloud_location: str,
                     reconstruction_type: ReconstructionType = ReconstructionType.ALL):
    """
    Convenience function for a list of JSON neuron files.  Primarily used for development and testing.
    """
    neurons = list()

    for json_file in json_files:
        with open(json_file) as f:
            data = json.load(f)
            neurons.append(data["neurons"][0])

    create_from_dict(neurons, cloud_location, reconstruction_type=reconstruction_type)


def create_from_data(neuron: dict, cloud_location: str, preferred_id: int = None,
                     reconstruction_type: ReconstructionType = ReconstructionType.ALL) -> int:
    """
    Add an individual neuron to the precomputed dataset.
    """
    ids = create_from_dict([neuron], cloud_location, [preferred_id], reconstruction_type)

    return ids[0] if len(ids) > 0 else None


def create_from_dict(neurons: List[dict], cloud_location: str, preferred_ids: List[int] = None,
                     reconstruction_type: ReconstructionType = ReconstructionType.ALL) -> List[int]:
    """
    Add one or more neurons to the precomputed dataset.
    """
    cv = _create_dataset_info(cloud_location)

    skeletons = list()

    cf = CloudFiles(cloud_location)

    existing = cf.get("segment_properties/info.pickle")

    if existing is not None:
        segment_info = pickle.loads(existing)
    else:
        segment_info = SegmentInfo()

    ids = list()

    for idx, neuron in enumerate(neurons):
        skeleton_id = None
        # For the NMCP portal worker, an assigned skeleton id will be pass directly.  For other uses or testing,
        # fall back to parsing the idString with the assumptions is in the N#### format.  If that fails, skip.
        # This is not a general purpose loader/generator.
        if preferred_ids is not None and len(preferred_ids) > idx and preferred_ids[idx] is not None:
            skeleton_id = preferred_ids[idx]
        elif "idString" in neuron:
            try:
                skeleton_id = int(neuron["idString"][1:4])
            except:
                pass  # Ok to fail for some unsupported skeleton id interpretation.

        if skeleton_id is not None:
            try:
                # TODO: Could be left in an odd state if the skeleton is created but segment_info append fails.
                skeleton, properties = _load_from_dict(skeleton_id, neuron, reconstruction_type)
                skeletons.append(skeleton)
                segment_info.append(skeleton_id, properties)
                ids.append(skeleton_id)
            except:
                logger.error(f"Could not load skeleton {skeleton_id}", None, exc_info=True)

    cv.skeleton.upload(skeletons)

    _create_segment_properties(cloud_location, segment_info)

    return ids


def remove_skeleton(skeleton_id: int, cloud_location: str) -> bool:
    cf = CloudFiles(cloud_location)

    existing = cf.get("segment_properties/info.pickle")

    if existing is None:
        return False

    segment_info = pickle.loads(existing)

    segment_info.remove(skeleton_id)

    _create_segment_properties(cloud_location, segment_info)

    cf.delete(f"skeleton/{skeleton_id}")

    return True


def list_skeletons(cloud_location: str) -> List[int]:
    cf = CloudFiles(cloud_location)

    existing = cf.get("segment_properties/info.pickle")

    if existing is None:
        return []

    segment_info = pickle.loads(existing)

    return segment_info.ids


def _load_from_dict(skeleton_id: int, data: dict, reconstruction_type: ReconstructionType) -> (Skeleton,
                                                                                               NmcpPropertyValues):
    sk = create_skeleton(skeleton_id, data, reconstruction_type)
    values = _extract_segment_properties(data)
    return sk, values


def _create_dataset_info(cloud_location: str) -> CloudVolume:
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


def _extract_segment_properties(data: dict) -> NmcpPropertyValues:
    soma_allen_id = data["soma"]["allenId"]

    label = (data["idString"])

    sample = data["sample"]
    if sample is not None and "strain" in sample and sample["strain"] is not None:
        strain = sample["strain"]
    else:
        strain = "unknown"

    # segment_property_info.append(segment_id, label, strain, soma_allen_id)
    return NmcpPropertyValues(label, strain, soma_allen_id)


def _create_segment_properties(cloud_location: str, segment_property_info: SegmentInfo):
    """ One per dataset"""
    cf = CloudFiles(cloud_location)

    # The required precomputed segment properties info file.
    cf.put_json("segment_properties/info", segment_property_info.as_dict())

    # Stash the internal representation of the segment properties info for additional context that would need to be
    # rebuilt if deserializing `info`.
    cf.put("segment_properties/info.pickle", pickle.dumps(segment_property_info))
