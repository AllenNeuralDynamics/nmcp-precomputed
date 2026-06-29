import json

import pytest
from fastapi.testclient import TestClient

import nmcp.api.app
from nmcp import create_from_reconstruction
from nmcp.api import create_app
from nmcp.data.portal_reconstruction import PortalReconstruction
from test_util import load_reconstruction


@pytest.fixture
def client(tmp_path):
    return TestClient(create_app(f"file://{tmp_path / 'worker'}"))


def _body(location: str, segment_id: int | None = None, reconstruction: PortalReconstruction | dict | None = None) -> dict:
    body = {"location": location, "reconstruction": reconstruction or load_reconstruction()}
    if segment_id is not None:
        body["segmentId"] = segment_id
    return body


def _segment_ids(directory) -> list[str]:
    with open(directory / "segment_properties" / "info") as f:
        return json.load(f)["inline"]["ids"]


def _post(client, body) -> dict:
    response = client.post("/generateskeleton", json=body)
    assert response.status_code == 200
    return response.json()


def test_root_reports_service_name(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == "NMCP Precomputed API"


def test_generates_dataset_with_default_segment_id(client, tmp_path):
    location = f"file://{tmp_path / 'out'}"

    output = _post(client, _body(location))

    assert output["errorKind"] is None
    assert output["result"] == {"location": location, "segmentId": 1, "nodeCount": 9, "edgeCount": 8}
    assert output["serviceVersion"]
    assert output["reconstructionId"] == load_reconstruction()["id"]
    assert (tmp_path / "out" / "skeleton" / "1").is_file()
    assert _segment_ids(tmp_path / "out") == ["1"]


def test_uses_requested_segment_id(client, tmp_path):
    output = _post(client, _body(f"file://{tmp_path / 'out'}", 42))

    assert output["result"]["segmentId"] == 42
    assert (tmp_path / "out" / "skeleton" / "42").is_file()
    assert _segment_ids(tmp_path / "out") == ["42"]


def test_output_matches_worker_output(client, tmp_path):
    _post(client, _body(f"file://{tmp_path / 'api'}"))
    create_from_reconstruction(load_reconstruction(), f"file://{tmp_path / 'worker-path'}", 1)

    for name in ["info", "skeleton/info", "skeleton/1", "segment_properties/info"]:
        assert (tmp_path / "api" / name).read_bytes() == (tmp_path / "worker-path" / name).read_bytes(), name


@pytest.mark.parametrize("suffix", ["", "/", "/full"])
@pytest.mark.parametrize("prefix", ["", "precomputed://"])
def test_rejects_location_at_or_under_worker_output(client, tmp_path, prefix, suffix):
    output = _post(client, _body(f"{prefix}file://{tmp_path / 'worker'}{suffix}"))

    assert output["errorKind"] == "ProtectedLocation"
    assert output["result"] is None
    assert not (tmp_path / "worker").exists()


def test_allows_sibling_of_worker_output(client, tmp_path):
    output = _post(client, _body(f"file://{tmp_path / 'worker-ondemand'}"))

    assert output["errorKind"] is None
    assert (tmp_path / "worker-ondemand" / "skeleton" / "1").is_file()


def test_accepts_precomputed_suffix_spelling(client, tmp_path):
    output = _post(client, _body(f"file://{tmp_path / 'suffix'}|precomputed:"))

    assert output["errorKind"] is None
    assert output["result"]["location"] == f"file://{tmp_path / 'suffix'}"
    assert (tmp_path / "suffix" / "info").is_file()
    assert (tmp_path / "suffix" / "skeleton" / "1").is_file()


def test_rejects_suffix_spelling_under_worker_output(client, tmp_path):
    output = _post(client, _body(f"file://{tmp_path / 'worker'}/full|precomputed:"))

    assert output["errorKind"] == "ProtectedLocation"


def test_rejects_symlinked_spelling_of_worker_output(client, tmp_path):
    (tmp_path / "worker").mkdir()
    (tmp_path / "link").symlink_to(tmp_path / "worker")

    output = _post(client, _body(f"file://{tmp_path / 'link'}/full"))

    assert output["errorKind"] == "ProtectedLocation"
    assert list((tmp_path / "worker").iterdir()) == []


def test_rejects_location_without_protocol(client):
    output = _post(client, _body("relative/dir"))

    assert output["errorKind"] == "InvalidLocation"
    assert output["result"] is None


def test_reports_generation_failure(client, tmp_path):
    reconstruction = load_reconstruction()
    soma = next(n for n in reconstruction["nodes"] if n["parentIndex"] == -1)
    soma["parentIndex"] = 2

    output = _post(client, _body(f"file://{tmp_path / 'out'}", reconstruction=reconstruction))

    assert output["errorKind"] == "GenerationError"
    assert output["result"] is None
    assert output["errorInfo"].startswith("StopIteration")


def test_reports_generation_exception_detail(client, tmp_path, monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("upload failed")

    monkeypatch.setattr(nmcp.api.app, "create_standalone_from_reconstruction", fail)

    output = _post(client, _body(f"file://{tmp_path / 'out'}"))

    assert output["errorKind"] == "GenerationError"
    assert output["errorInfo"] == "RuntimeError: upload failed"


@pytest.mark.parametrize("segment_id", [0, -1])
def test_rejects_invalid_segment_id(client, tmp_path, segment_id):
    response = client.post("/generateskeleton", json=_body(f"file://{tmp_path / 'out'}", segment_id))

    assert response.status_code == 422


def test_rejects_malformed_body(client, tmp_path):
    reconstruction = {k: v for k, v in load_reconstruction().items() if k != "nodes"}

    response = client.post("/generateskeleton", json=_body(f"file://{tmp_path / 'out'}", reconstruction=reconstruction))

    assert response.status_code == 422
