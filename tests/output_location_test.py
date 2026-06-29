import itertools
import os

import pytest
from cloudfiles import paths

from nmcp.api.output_location import parse_output_location

_alias_counter = itertools.count()


def _under(candidate: str, protected: str) -> bool:
    return parse_output_location(candidate).is_at_or_under(parse_output_location(protected))


@pytest.mark.parametrize("location", [
    "s3://bucket/ngv01",
    "s3://bucket/ngv01/",
    "precomputed://s3://bucket/ngv01",
    "s3://bucket/ngv01|precomputed:",
    "s3://bucket/ngv01/|precomputed:",
    "  s3://bucket/ngv01  ",
])
def test_spellings_normalize_to_same_location(location):
    parsed = parse_output_location(location)

    assert parsed.cloudpath == "s3://bucket/ngv01"
    assert not parsed.cloudpath.startswith("precomputed://")
    assert (parsed.protocol, parsed.host, parsed.bucket, parsed.path) == ("s3", None, "bucket", "ngv01")


@pytest.mark.parametrize("candidate, expected", [
    ("s3://bucket/ngv01", True),
    ("s3://bucket/ngv01/full", True),
    ("s3://bucket/ngv01-ondemand", False),
    ("s3://bucket", False),
    ("s3://other/ngv01", False),
    ("gs://bucket/ngv01", False),
])
def test_at_or_under(candidate, expected):
    assert _under(candidate, "s3://bucket/ngv01") is expected


def test_bucket_root_protects_whole_bucket():
    assert _under("s3://bucket/anything", "s3://bucket")


@pytest.fixture
def alias():
    name = f"nmcptest{os.getpid()}x{next(_alias_counter)}"
    paths.add_alias(name, "s3://http://localhost:9999/")
    try:
        yield name
    finally:
        paths.remove_alias(name)


def test_alias_resolves_to_same_location(alias):
    assert _under(f"{alias}://bucket/ngv01/full", "s3://http://localhost:9999/bucket/ngv01")


def test_alias_spelling_is_kept_in_cloudpath(alias):
    assert parse_output_location(f"{alias}://bucket/ngv01/").cloudpath == f"{alias}://bucket/ngv01"


def test_file_dot_segments_are_folded(tmp_path):
    assert _under(f"file://{tmp_path}/a/../a/ngv01/x", f"file://{tmp_path}/a/ngv01")


def test_symlinked_spelling_is_resolved(tmp_path):
    (tmp_path / "real" / "worker").mkdir(parents=True)
    (tmp_path / "link").symlink_to(tmp_path / "real")

    assert _under(f"file://{tmp_path}/link/worker/full", f"file://{tmp_path}/real/worker")
    assert _under(f"file://{tmp_path}/link/worker", f"file://{tmp_path}/real/worker")


def test_file_root_protects_every_local_path():
    assert _under("file:///tmp/output", "file:///")


def test_file_root_cloudpath_is_kept():
    assert parse_output_location("file:///").cloudpath == "file:///"


def test_file_sibling_is_not_under(tmp_path):
    assert not _under(f"file://{tmp_path}/a/ngv01-x", f"file://{tmp_path}/a/ngv01")


@pytest.mark.parametrize("location", [
    "",
    "   ",
    "precomputed://",
    "relative/dir",
    "/abs/dir",
    "S3://bucket/a",
    "ftp://host/x",
    "zarr://s3://bucket/a",
    "s3://bucket/a|zarr:",
])
def test_invalid_locations_raise(location):
    with pytest.raises(ValueError):
        parse_output_location(location)


def test_bare_path_accepted_without_required_protocol(tmp_path):
    parsed = parse_output_location(str(tmp_path / "worker"), require_protocol=False)

    assert parsed.protocol == "file"
    assert parsed.path == os.path.realpath(tmp_path / "worker")
    assert parsed.cloudpath == f"file://{tmp_path / 'worker'}"


def test_wrong_format_rejected_without_required_protocol():
    with pytest.raises(ValueError):
        parse_output_location("s3://bucket/a|zarr:", require_protocol=False)
