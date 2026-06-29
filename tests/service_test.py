import logging
import threading

import pytest

import nmcp.precomputed_worker
import nmcp.service


@pytest.fixture
def calls(monkeypatch):
    recorded = []
    sentinel = object()

    def recorder(name, result=None):
        def stub(*args):
            recorded.append((name, args))
            return result

        return stub

    monkeypatch.setattr(nmcp.service, "create_app", recorder("create_app", sentinel))
    monkeypatch.setattr(nmcp.service, "load_structure_tree", recorder("load_structure_tree"))
    monkeypatch.setattr(nmcp.service, "start", recorder("start"))
    monkeypatch.setattr(nmcp.service, "serve", recorder("serve"))

    return recorded, sentinel


def test_startup_order(calls):
    recorded, sentinel = calls

    nmcp.service.run("http://unused", "key", "file:///tmp/x/")

    assert [name for name, _ in recorded] == ["create_app", "load_structure_tree", "start", "serve"]

    arguments = dict(recorded)
    assert arguments["create_app"] == ("file:///tmp/x",)
    assert arguments["start"] == ("http://unused", "key", "file:///tmp/x")
    assert arguments["serve"] == (sentinel,)


def test_worker_receives_normalized_output(monkeypatch):
    folders = []
    pending = []
    scheduled = threading.Event()

    def record_pending(client, output_location):
        pending.append(output_location)
        scheduled.set()

    monkeypatch.setattr(nmcp.service, "create_app", lambda output: object())
    monkeypatch.setattr(nmcp.service, "load_structure_tree", lambda: None)
    monkeypatch.setattr(nmcp.service, "serve", lambda app: None)
    monkeypatch.setattr(nmcp.precomputed_worker, "ensure_bucket_folders", folders.append)
    monkeypatch.setattr(nmcp.precomputed_worker, "RemoteDataClient", lambda url, auth_key: object())
    monkeypatch.setattr(nmcp.precomputed_worker, "process_pending", record_pending)

    nmcp.service.run("http://unused", "key", "precomputed://s3://bucket/ngv01/")

    assert scheduled.wait(5)
    assert folders == ["s3://bucket/ngv01"]
    assert pending == ["s3://bucket/ngv01"]


def test_non_normalized_output_logs_warning(calls, caplog):
    with caplog.at_level(logging.WARNING, logger="nmcp.service"):
        nmcp.service.run("http://unused", "key", "s3://bucket/ngv01/")

    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert "s3://bucket/ngv01/" in warnings[0].getMessage()
    assert "'s3://bucket/ngv01'" in warnings[0].getMessage()

    caplog.clear()

    with caplog.at_level(logging.WARNING, logger="nmcp.service"):
        nmcp.service.run("http://unused", "key", "s3://bucket/ngv01")

    assert [r for r in caplog.records if r.levelno == logging.WARNING] == []


def test_invalid_worker_output_stops_startup(calls):
    recorded, _ = calls

    with pytest.raises(ValueError):
        nmcp.service.run("http://unused", "key", "s3://bucket/x|zarr:")

    assert recorded == []


def test_structure_tree_failure_stops_startup(calls, monkeypatch):
    recorded, _ = calls

    def fail():
        raise RuntimeError("allen api unreachable")

    monkeypatch.setattr(nmcp.service, "load_structure_tree", fail)

    with pytest.raises(RuntimeError):
        nmcp.service.run("http://unused", "key", "file:///tmp/x")

    assert [name for name, _ in recorded] == ["create_app"]
