import threading
from typing import cast

import nmcp.precomputed_worker as precomputed_worker
from nmcp.data import PrecomputedEntry, RemoteDataClient
from test_util import load_reconstruction


class FakeClient:
    def __init__(self):
        self.marks = []

    @staticmethod
    def _pending():
        return [PrecomputedEntry(id="e1", skeletonId=5, version=None, reconstructionId="r1", generatedAt=None)]

    def find_atlas_pending(self):
        return self._pending()

    def find_specimen_space_pending(self):
        return self._pending()

    def get_exported_atlas_space_reconstruction_data(self, reconstruction_id):
        return load_reconstruction()

    def get_exported_specimen_space_reconstruction_data(self, reconstruction_id):
        return load_reconstruction()

    def __getattr__(self, name):
        if name.startswith("mark_"):
            return lambda entry_id: self.marks.append((name, entry_id))
        raise AttributeError(name)


def _fail(*args, **kwargs):
    raise RuntimeError("generation failed")


def test_successful_atlas_generation_is_marked_generated(tmp_path):
    client = FakeClient()

    assert precomputed_worker.process_atlas_pending(cast(RemoteDataClient, client), f"file://{tmp_path}")

    assert client.marks == [("mark_atlas_generated", "e1")]
    for variant in ["full", "axon", "dendrite"]:
        assert (tmp_path / variant / "skeleton" / "5").is_file(), variant


def test_failed_atlas_generation_is_marked_failed(tmp_path, monkeypatch):
    monkeypatch.setattr(precomputed_worker, "create_from_reconstruction", _fail)
    client = FakeClient()

    precomputed_worker.process_atlas_pending(cast(RemoteDataClient, client), f"file://{tmp_path}")

    assert client.marks == [("mark_atlas_failed_generate", "e1")]


def test_failed_specimen_generation_is_marked_failed(tmp_path, monkeypatch):
    monkeypatch.setattr(precomputed_worker, "create_from_reconstruction", _fail)
    client = FakeClient()

    precomputed_worker.process_specimen_pending(cast(RemoteDataClient, client), f"file://{tmp_path}")

    assert client.marks == [("mark_specimen_failed_generate", "e1")]


def test_start_schedules_first_cycle_on_daemon_thread(tmp_path, monkeypatch):
    ran = threading.Event()
    threads = []

    def record(client, output_location):
        threads.append(threading.current_thread())
        ran.set()

    monkeypatch.setattr(precomputed_worker, "RemoteDataClient", lambda url, auth_key: object())
    monkeypatch.setattr(precomputed_worker, "process_pending", record)

    precomputed_worker.start("http://unused", "key", f"file://{tmp_path}")

    assert ran.wait(5)
    assert threads[0] is not threading.current_thread()
    assert threads[0].daemon
