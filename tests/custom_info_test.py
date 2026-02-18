import copy
import json
import os
import shutil
import tempfile

import pytest
from cloudvolume import CloudVolume

from nmcp import create_from_json_files, create_from_data, extract_neuron_properties, SkeletonComponents
from test_utl import verify_precomputed_file


def _get_neuron(name: str = "small.json"):
    json_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "fixtures", name))

    with open(json_file) as f:
        data = json.load(f)
        return data["neurons"][0]


def _create_info(resolution: list[int], include_segment_properties: bool = True) -> dict:
    info = CloudVolume.create_new_info(
        num_channels=1,
        layer_type="segmentation",
        data_type="uint64",
        encoding="raw",
        resolution=resolution,
        voxel_offset=[0, 0, 0],
        skeletons="skeleton",
        chunk_size=[64, 64, 64],
        volume_size=[800, 900, 1000],
    )

    if include_segment_properties:
        info["segment_properties"] = "segment_properties"

    return info


def test_create_from_json_with_custom_info():
    temp_dir = tempfile.mkdtemp()
    try:
        json_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "fixtures", "small.json"))
        custom_info = _create_info([400, 500, 600])

        create_from_json_files([json_file], f"file://{temp_dir}", info=custom_info)

        verify_precomputed_file(temp_dir, 40, 63803)

        with open(os.path.join(temp_dir, "info")) as f:
            dataset_info = json.load(f)

        assert dataset_info["scales"][0]["resolution"] == [400, 500, 600]
        assert dataset_info["scales"][0]["chunk_sizes"][0] == [64, 64, 64]
        assert dataset_info["scales"][0]["size"] == [800, 900, 1000]
    finally:
        shutil.rmtree(temp_dir)


def test_custom_info_resolution_sets_skeleton_transform():
    temp_dir = tempfile.mkdtemp()
    try:
        json_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "fixtures", "small.json"))

        create_from_json_files([json_file], f"file://{temp_dir}", info=_create_info([410, 520, 630]))

        with open(os.path.join(temp_dir, "skeleton", "info")) as f:
            skeleton_info = json.load(f)

        assert skeleton_info["transform"] == [410, 0, 0, 0, 0, 520, 0, 0, 0, 0, 630, 0]
    finally:
        shutil.rmtree(temp_dir)


def test_custom_info_autofills_segment_properties():
    temp_dir = tempfile.mkdtemp()
    try:
        json_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "fixtures", "small.json"))

        create_from_json_files(
            [json_file],
            f"file://{temp_dir}",
            info=_create_info([250, 260, 270], include_segment_properties=False),
        )

        with open(os.path.join(temp_dir, "info")) as f:
            dataset_info = json.load(f)

        assert dataset_info["segment_properties"] == "segment_properties"
    finally:
        shutil.rmtree(temp_dir)


def test_custom_info_is_not_mutated():
    temp_dir = tempfile.mkdtemp()
    try:
        neuron = _get_neuron()

        properties = extract_neuron_properties(neuron)
        axon = SkeletonComponents.create(neuron["axon"])
        dendrite = SkeletonComponents.create(neuron["dendrite"])

        custom_info = _create_info([700, 800, 900], include_segment_properties=False)
        original_info = copy.deepcopy(custom_info)

        create_from_data(axon, dendrite, properties, f"file://{temp_dir}", 51, info=custom_info)
        create_from_data(axon, dendrite, properties, f"file://{temp_dir}", 52, info=custom_info)

        verify_precomputed_file(temp_dir, 51, 63803)
        verify_precomputed_file(temp_dir, 52, 63803)

        assert custom_info == original_info
        assert "segment_properties" not in custom_info
    finally:
        shutil.rmtree(temp_dir)


def test_invalid_custom_info_raises_before_write():
    temp_dir = tempfile.mkdtemp()
    try:
        json_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "fixtures", "small.json"))

        with pytest.raises(ValueError, match="resolution"):
            create_from_json_files(
                [json_file],
                f"file://{temp_dir}",
                info={"segment_properties": "segment_properties"},
            )

        assert not os.path.exists(os.path.join(temp_dir, "info"))
    finally:
        shutil.rmtree(temp_dir)
