import threading
import time

import pytest

from nmcp.precomputed import segment_tag_property


class _FakeTree:
    def get_structures_by_id(self, ids):
        return [{"acronym": "X", "name": "Y"}]


@pytest.fixture
def fake_cache(monkeypatch):
    constructed = []

    class FakeMouseConnectivityCache:
        def __init__(self, resolution):
            constructed.append(resolution)

        def get_structure_tree(self):
            time.sleep(0.2)
            return _FakeTree()

    monkeypatch.setattr(segment_tag_property, "_structure_id_lookup", None)
    monkeypatch.setattr(segment_tag_property, "MouseConnectivityCache", FakeMouseConnectivityCache)

    return constructed


def test_concurrent_first_use_loads_once(fake_cache):
    barrier = threading.Barrier(4)
    results = []

    def lookup():
        barrier.wait()
        results.append(segment_tag_property._use_soma_lookup(1))

    threads = [threading.Thread(target=lookup) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)

    assert len(fake_cache) == 1
    assert results == [("X", "Y")] * 4


def test_loaded_lookup_never_takes_the_lock(fake_cache):
    segment_tag_property.load_structure_tree()

    results = []
    thread = threading.Thread(target=lambda: results.append(segment_tag_property._use_soma_lookup(1)))

    segment_tag_property._structure_id_lookup_lock.acquire()
    try:
        thread.start()
        thread.join(timeout=5)

        assert not thread.is_alive()
        assert results == [("X", "Y")]
    finally:
        segment_tag_property._structure_id_lookup_lock.release()
