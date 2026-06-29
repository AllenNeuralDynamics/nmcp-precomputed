import json
import logging
import pickle
from copy import deepcopy
from typing import cast

from typing_extensions import List

from cloudvolume import CloudVolume, Skeleton
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
    except Exception:
        logger.exception("could not create bucket folders")


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
                                    cloud_files_info: dict | None = None) -> int:
    """
    Add or replace one skeleton in an incrementally maintained dataset, merging its segment properties with those
    already recorded in `segment_properties/info.pickle`. Raises on any failure.
    """
    cv = _create_dataset_info(cloud_location, cloud_files_info)

    segment_info = _load_segment_info(cloud_location)

    _add_skeleton(cv, components, properties, skeleton_id, segment_info)

    _create_segment_properties(cloud_location, segment_info)

    return skeleton_id


def create_standalone_from_reconstruction(reconstruction: PortalReconstruction, cloud_location: str,
                                          skeleton_id: int, cloud_files_info: dict) -> Skeleton:
    """
    Write a complete dataset holding only this skeleton (full structure). Existing content at the location is
    overwritten but not cleared, and `segment_properties/info.pickle` is neither read nor written. Raises on any
    failure.
    """
    components = SkeletonComponents(reconstruction["nodes"])

    properties = extract_reconstruction_properties(reconstruction)

    cv = _create_dataset_info(cloud_location, cloud_files_info)

    segment_info = SegmentInfo()

    skeleton = _add_skeleton(cv, components, properties, skeleton_id, segment_info)

    _put_segment_properties_info(cloud_location, segment_info)

    return skeleton


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


def default_cloudvolume_info() -> dict:
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
        return default_cloudvolume_info()

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


def _load_segment_info(cloud_location: str) -> SegmentInfo:
    existing = cast(bytes, CloudFiles(cloud_location).get("segment_properties/info.pickle"))

    if existing is not None:
        return pickle.loads(existing)

    return SegmentInfo()


def _add_skeleton(cv: CloudVolume, components: SkeletonComponents, properties: SegmentPropertyValues,
                  skeleton_id: int, segment_info: SegmentInfo) -> Skeleton:
    skeleton = components.create_skeleton(skeleton_id)

    segment_info.append(skeleton_id, properties)

    cv.skeleton.upload(skeleton)

    return skeleton


def _put_segment_properties_info(cloud_location: str, segment_property_info: SegmentInfo):
    # The required precomputed segment properties info file.
    CloudFiles(cloud_location).put_json("segment_properties/info", segment_property_info.as_dict())


def _create_segment_properties(cloud_location: str, segment_property_info: SegmentInfo):
    """ One per dataset"""
    _put_segment_properties_info(cloud_location, segment_property_info)

    cf = CloudFiles(cloud_location)

    # Stash the internal representation of the segment properties info for additional context that would need to be
    # rebuilt if deserializing `info`.
    cf.put("segment_properties/info.pickle", pickle.dumps(segment_property_info))
