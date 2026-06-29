import copy
import json

from cloudvolume import CloudVolume

from nmcp import create_standalone_from_reconstruction, default_cloudvolume_info
from test_util import load_reconstruction


def _segment_properties(directory) -> dict:
    with open(directory / "segment_properties" / "info") as f:
        return json.load(f)


def test_writes_complete_single_segment_dataset(tmp_path):
    location = f"file://{tmp_path}"

    skeleton = create_standalone_from_reconstruction(load_reconstruction(), location, 7,
                                                     cloud_files_info=default_cloudvolume_info())

    for name in ["info", "skeleton/info", "skeleton/7", "segment_properties/info"]:
        assert (tmp_path / name).is_file(), name
    assert not (tmp_path / "segment_properties" / "info.pickle").exists()

    segment_properties = _segment_properties(tmp_path)
    assert segment_properties["inline"]["ids"] == ["7"]

    values = [v for p in segment_properties["inline"]["properties"] if p.get("type") != "tags" for v in p["values"]]
    assert "N004-648434" in values
    assert "Dbh-Cre_KI" in values

    tags = next(p for p in segment_properties["inline"]["properties"] if p.get("type") == "tags")
    assert len(tags["tags"]) == 1

    assert CloudVolume(location).skeleton.get(7).vertices.shape == (9, 3)
    assert len(skeleton.vertices) == 9
    assert len(skeleton.edges) == 8


def test_overwrites_previous_dataset(tmp_path):
    location = f"file://{tmp_path}"

    create_standalone_from_reconstruction(load_reconstruction(), location, 7, default_cloudvolume_info())
    create_standalone_from_reconstruction(load_reconstruction(), location, 8, default_cloudvolume_info())

    assert _segment_properties(tmp_path)["inline"]["ids"] == ["8"]
    assert (tmp_path / "skeleton" / "8").is_file()
    # The location is overwritten, not cleared.
    assert (tmp_path / "skeleton" / "7").is_file()


def test_ignores_existing_pickle(tmp_path):
    pickle_file = tmp_path / "segment_properties" / "info.pickle"
    pickle_file.parent.mkdir(parents=True)
    pickle_file.write_bytes(b"not a pickle")

    create_standalone_from_reconstruction(load_reconstruction(), f"file://{tmp_path}", 7, default_cloudvolume_info())

    assert pickle_file.read_bytes() == b"not a pickle"


def test_uses_passed_info(tmp_path):
    info = CloudVolume.create_new_info(num_channels=1, layer_type="segmentation", data_type="uint64",
                                       encoding="raw", resolution=[400, 500, 600], voxel_offset=[0, 0, 0],
                                       skeletons="skeleton", chunk_size=[64, 64, 64], volume_size=[800, 900, 1000])
    original = copy.deepcopy(info)

    create_standalone_from_reconstruction(load_reconstruction(), f"file://{tmp_path}", 7, cloud_files_info=info)

    with open(tmp_path / "info") as f:
        assert json.load(f)["scales"][0]["resolution"] == [400, 500, 600]

    assert info == original
