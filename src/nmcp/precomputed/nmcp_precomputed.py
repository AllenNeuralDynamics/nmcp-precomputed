import json
import logging
import pickle
from copy import deepcopy
from typing import cast

from typing_extensions import List

from cloudvolume import CloudVolume
from cloudfiles import CloudFiles

from .nmcp_skeleton import vertex_attributes, SkeletonComponents
from .segment_info import SegmentInfo, SegmentPropertyValues
from ..data.portal_reconstruction import PortalReconstruction
from .neuron_structure import NeuronStructure

logger = logging.getLogger(__name__)


def ensure_bucket_folders(cloud_location: str):
    try:
        cf = CloudFiles(cloud_location)
        cf.touch("full/temp.txt")
        cf.touch("axon/temp.txt")
        cf.touch("dendrite/temp.txt")
        cf.touch("specimen/temp.txt")
    except Exception as ex:
        logger.error("could not create bucket folders", None, exc_info=False)


def create_from_json_files(json_files: List[str], cloud_location: str, info: dict | None = None,
                           structure: NeuronStructure | None = None) -> List[int]:
    """
    Convenience function for a list of portal-formatted JSON reconstruction files.
    """

    ids: List[int] = []

    for json_file in json_files:
        with open(json_file) as f:
            data: PortalReconstruction = json.load(f)
            skeleton_id = create_from_reconstruction(data, cloud_location, structure=structure, cloud_files_info=info)
            if skeleton_id is not None:
                ids.append(skeleton_id)

    return ids


def create_from_reconstruction(reconstruction: PortalReconstruction, cloud_location: str,
                               skeleton_id: int | None = None, structure: NeuronStructure | None = None,
                               cloud_files_info: dict | None = None) -> int | None:
    if skeleton_id is None:
        if "neuron" in reconstruction and "label" in reconstruction["neuron"]:
            try:
                skeleton_id = int(reconstruction["neuron"]["label"][1:4])
            except:
                pass  # Ok to fail for some unsupported skeleton id interpretation.

    if skeleton_id is not None:
        components = SkeletonComponents(reconstruction["nodes"], structure)

        properties = extract_reconstruction_properties(reconstruction)

        return create_from_skeleton_components(components, properties, cloud_location, skeleton_id, cloud_files_info)

    return None


def create_from_skeleton_components(components: SkeletonComponents, properties: SegmentPropertyValues,
                                    cloud_location: str, skeleton_id: int,
                                    cloud_files_info: dict | None = None) -> int | None:
    """
    Add one or more neurons to the precomputed dataset.
    """
    cv = _create_dataset_info(cloud_location, cloud_files_info)

    # remove_skeleton(cloud_location, skeleton_id)

    try:
        cf = CloudFiles(cloud_location)
    except Exception as ex:
        logger.error("could not create cloud files", None, exc_info=False)
        return None

    try:
        existing = cast(bytes, cf.get("segment_properties/info.pickle"))
    except Exception as ex:
        logger.error("could not ask for get segment info", None, exc_info=False)
        return None

    try:
        if existing is not None:
            segment_info = pickle.loads(existing)
        else:
            segment_info = SegmentInfo()
    except Exception as ex:
        logger.error("could not get segment info", None, exc_info=False)
        return None

    try:
        skeleton = components.create_skeleton(skeleton_id)
    except Exception as ex:
        logger.error("could not create skeleton", None, exc_info=False)
        return None

    try:
        segment_info.append(skeleton_id, properties)
    except Exception as ex:
        logger.error("could not append segment info", None, exc_info=False)
        return None

    try:
        # TODO: Could be left in an odd state segment_info is appended but skeleton upload fails.
        cv.skeleton.upload(skeleton)
    except Exception as ex:
        logger.error("could not upload skeleton", None, exc_info=False)
        return None

    try:
        _create_segment_properties(cloud_location, segment_info)
    except Exception as ex:
        logger.error(f"could create segment properties {skeleton_id}", None, exc_info=True)
        logger.exception(ex, exc_info=True)

    return skeleton_id


def remove_skeleton(cloud_location: str, skeleton_id: int) -> bool:
    cf = CloudFiles(cloud_location)

    existing = cast(bytes, cf.get("segment_properties/info.pickle"))

    if existing is None:
        return False

    segment_info = pickle.loads(existing)

    segment_info.remove(skeleton_id)

    _create_segment_properties(cloud_location, segment_info)

    cf.delete(f"skeleton/{skeleton_id}")

    return True


def list_skeletons(cloud_location: str) -> List[int]:
    cf = CloudFiles(cloud_location)

    existing = cast(bytes, cf.get("segment_properties/info.pickle"))

    if existing is None:
        return []

    segment_info = pickle.loads(existing)

    return segment_info.ids


def extract_reconstruction_properties(data: PortalReconstruction) -> SegmentPropertyValues:
    soma = next((n for n in data["nodes"] if n["structure"] == 1), None)

    if soma is not None and soma["atlasStructure"] is not None:
        soma_atlas_structure_id = soma["atlasStructure"]
    else:
        soma_atlas_structure_id = None

    label = f'{(data["neuron"]["label"])}-{(data["neuron"]["specimen"]["label"])}'

    specimen = data["neuron"]["specimen"]

    if specimen["genotype"] is not None:
        genotype = specimen["genotype"]
    else:
        genotype = "unknown"

    return SegmentPropertyValues(label, genotype, soma_atlas_structure_id)


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


def _create_segment_properties(cloud_location: str, segment_property_info: SegmentInfo):
    """ One per dataset"""
    cf = CloudFiles(cloud_location)

    # The required precomputed segment properties info file.
    cf.put_json("segment_properties/info", segment_property_info.as_dict())

    # Stash the internal representation of the segment properties info for additional context that would need to be
    # rebuilt if deserializing `info`.
    cf.put("segment_properties/info.pickle", pickle.dumps(segment_property_info))
