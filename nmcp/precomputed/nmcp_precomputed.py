import json
import logging
import pickle
from copy import deepcopy
from typing import List

from cloudvolume import CloudVolume
from cloudfiles import CloudFiles

from .nmcp_skeleton import (create_skeleton, vertex_attributes, create_skeleton_components,
                            SkeletonComponents)
from .segment_info import SegmentInfo, NmcpPropertyValues

logger = logging.getLogger(__name__)


def ensure_bucket_folders(cloud_location: str):
    try:
        cf = CloudFiles(cloud_location)
        cf.touch("full/temp.txt")
        cf.touch("axon/temp.txt")
        cf.touch("dendrite/temp.txt")
    except Exception as ex:
        logger.error("could not create bucket folders", None, exc_info=False)


def create_from_json_files(json_files: [], cloud_location: str, info: dict | None = None):
    """
    Convenience function for a list of JSON neuron files.  Primarily used for development and testing.
    """
    for json_file in json_files:
        with open(json_file) as f:
            data = json.load(f)
            create_from_dict(data["neurons"][0], cloud_location, info)


def create_from_dict(neuron: dict, cloud_location: str, info: dict | None = None):
    skeleton_id = None

    if "idString" in neuron:
        try:
            skeleton_id = int(neuron["idString"][1:4])
        except:
            pass  # Ok to fail for some unsupported skeleton id interpretation.

    if skeleton_id is not None:
        axon, dendrite = create_skeleton_components(neuron)
        properties = extract_neuron_properties(neuron)
        create_from_data(axon, dendrite, properties, cloud_location, skeleton_id, info)


def create_from_data(axon: SkeletonComponents, dendrite: SkeletonComponents, properties: NmcpPropertyValues,
                     cloud_location: str, skeleton_id: int, info: dict | None = None):
    """
    Add one or more neurons to the precomputed dataset.
    """
    cv = _create_dataset_info(cloud_location, info)

    # remove_skeleton(cloud_location, skeleton_id)

    try:
        cf = CloudFiles(cloud_location)
    except Exception as ex:
        logger.error("could not create cloud files", None, exc_info=False)
        return

    try:
        existing = cf.get("segment_properties/info.pickle")
    except Exception as ex:
        logger.error("could not ask for get segment info", None, exc_info=False)
        return

    try:
        if existing is not None:
            segment_info = pickle.loads(existing)
        else:
            segment_info = SegmentInfo()
    except Exception as ex:
        logger.error("could not get segment info", None, exc_info=False)
        return

    try:
        # TODO: Could be left in an odd state if the skeleton is created but segment_info append fails.
        skeleton = create_skeleton(skeleton_id, axon, dendrite)
    except Exception as ex:
        logger.error("could not create skeleton", None, exc_info=False)
        return

    try:
        segment_info.append(skeleton_id, properties)
    except Exception as ex:
        logger.error("could not append segment info", None, exc_info=False)
        return

    try:
        cv.skeleton.upload(skeleton)
    except Exception as ex:
        logger.error("could not upload skeleton", None, exc_info=False)
        return

    try:
        _create_segment_properties(cloud_location, segment_info)
    except Exception as ex:
        logger.error(f"could create segment properties {skeleton_id}", None, exc_info=True)
        logger.exception(ex, exc_info=True)


def remove_skeleton(cloud_location: str, skeleton_id: int) -> bool:
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


def _default_cloudvolume_info() -> dict:
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

    return info


def _extract_resolution(info_dict: dict) -> List[float]:
    resolution = None

    scales = info_dict.get("scales")
    if isinstance(scales, list) and len(scales) > 0 and isinstance(scales[0], dict):
        resolution = scales[0].get("resolution")

    if resolution is None:
        resolution = info_dict.get("resolution")

    if not isinstance(resolution, (list, tuple)) or len(resolution) != 3:
        raise ValueError("CloudVolume info must define a 3-value resolution.")

    values = []
    for value in resolution:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("CloudVolume resolution values must be numeric.")
        if value <= 0:
            raise ValueError("CloudVolume resolution values must be greater than zero.")
        values.append(value)

    return values


def _prepare_cloudvolume_info(info: dict | None) -> dict:
    if info is None:
        return _default_cloudvolume_info()

    if not isinstance(info, dict):
        raise ValueError("CloudVolume info must be provided as a dict.")

    prepared = deepcopy(info)

    if "segment_properties" not in prepared:
        prepared["segment_properties"] = "segment_properties"

    _extract_resolution(prepared)

    return prepared


def _create_dataset_info(cloud_location: str, info: dict | None = None) -> CloudVolume:
    """ Once per dataset """
    prepared_info = _prepare_cloudvolume_info(info)
    resolution = _extract_resolution(prepared_info)

    full_location = f"precomputed://{cloud_location}"

    logger.info(f"creating CloudVolume at {full_location}")

    cv = CloudVolume(full_location, info=prepared_info, compress=False)

    sk_info = cv.skeleton.meta.default_info()

    sk_info["transform"] = [resolution[0], 0, 0, 0, 0, resolution[1], 0, 0, 0, 0, resolution[2], 0]
    sk_info["vertex_attributes"] = vertex_attributes
    cv.skeleton.meta.info = sk_info
    cv.skeleton.meta.commit_info()

    cv.commit_info()

    return cv


def extract_neuron_properties(data: dict) -> NmcpPropertyValues:
    if "allenId" in data["soma"]:
        soma_allen_id = data["soma"]["allenId"]
    else:
        soma_allen_id = None

    label = (data["idString"])

    sample = data.get("sample")
    if sample is not None and "strain" in sample and sample["strain"] is not None:
        strain = sample["strain"]
    else:
        strain = "unknown"

    return NmcpPropertyValues(label, strain, soma_allen_id)


def _create_segment_properties(cloud_location: str, segment_property_info: SegmentInfo):
    """ One per dataset"""
    cf = CloudFiles(cloud_location)

    # The required precomputed segment properties info file.
    cf.put_json("segment_properties/info", segment_property_info.as_dict())

    # Stash the internal representation of the segment properties info for additional context that would need to be
    # rebuilt if deserializing `info`.
    cf.put("segment_properties/info.pickle", pickle.dumps(segment_property_info))
