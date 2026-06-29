import logging
import pickle

import pytest

import nmcp.precomputed.nmcp_precomputed as nmcp_precomputed
from nmcp import create_from_reconstruction, ensure_bucket_folders
from nmcp.precomputed.nmcp_skeleton import SkeletonComponents
from test_util import load_reconstruction


def test_successful_generation_returns_skeleton_id(tmp_path):
    assert create_from_reconstruction(load_reconstruction(), f"file://{tmp_path}", 5) == 5


def test_corrupt_segment_info_pickle_raises(tmp_path):
    pickle_file = tmp_path / "segment_properties" / "info.pickle"
    pickle_file.parent.mkdir(parents=True)
    pickle_file.write_bytes(b"not a pickle")

    with pytest.raises(pickle.UnpicklingError):
        create_from_reconstruction(load_reconstruction(), f"file://{tmp_path}", 5)


def test_skeleton_creation_failure_raises(tmp_path, monkeypatch):
    def fail(self, skeleton_id):
        raise RuntimeError("boom")

    monkeypatch.setattr(SkeletonComponents, "create_skeleton", fail)

    with pytest.raises(RuntimeError, match="boom"):
        create_from_reconstruction(load_reconstruction(), f"file://{tmp_path}", 5)

    assert not (tmp_path / "skeleton" / "5").exists()


def test_segment_properties_write_failure_raises(tmp_path, monkeypatch):
    def fail(cloud_location, segment_info):
        raise RuntimeError("write failed")

    monkeypatch.setattr(nmcp_precomputed, "_put_segment_properties_info", fail)

    with pytest.raises(RuntimeError, match="write failed"):
        create_from_reconstruction(load_reconstruction(), f"file://{tmp_path}", 5)


def test_bucket_folder_failure_is_logged_with_its_cause(monkeypatch, caplog):
    error = RuntimeError("no bucket")

    class FailingCloudFiles:
        def __init__(self, cloud_location):
            pass

        def touch(self, path):
            raise error

    monkeypatch.setattr(nmcp_precomputed, "CloudFiles", FailingCloudFiles)

    with caplog.at_level(logging.ERROR, logger=nmcp_precomputed.__name__):
        ensure_bucket_folders("file:///unused")

    records = [r for r in caplog.records if r.levelno == logging.ERROR]
    assert len(records) == 1
    assert records[0].getMessage() == "could not create bucket folders"
    assert records[0].exc_info[1] is error
