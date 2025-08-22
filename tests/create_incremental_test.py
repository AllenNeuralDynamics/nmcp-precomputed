import json
import os
import shutil
import tempfile

from nmcp import extract_neuron_properties, create_from_data, SkeletonComponents

from test_utl import verify_precomputed_file


def _get_neuron(name: str):
    json_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "fixtures", name))

    with open(json_file) as f:
        data = json.load(f)
        return data["neurons"][0]


def test_create_incremental():
    temp_dir = tempfile.mkdtemp()
    try:
        neuron = _get_neuron("small.json")

        properties = extract_neuron_properties(neuron)

        axon = SkeletonComponents.create(neuron["axon"])

        dendrite = SkeletonComponents.create(neuron["dendrite"])

        create_from_data(axon, dendrite, properties, f"file://{temp_dir}", 15)

        verify_precomputed_file(temp_dir, 15, 63803)
    finally:
        shutil.rmtree(temp_dir)


def test_incremental_chunked():
    temp_dir = tempfile.mkdtemp()
    try:
        neuron = _get_neuron("small.json")

        properties = extract_neuron_properties(neuron)

        chunk_size = 25000

        axon_source = neuron["axon"]
        axon = SkeletonComponents.create(axon_source[:chunk_size])
        for idx in range(chunk_size, len(axon_source), chunk_size):
            axon.append(axon_source[idx:idx + chunk_size])

        dendrite_source = neuron["dendrite"]
        dendrite = SkeletonComponents.create(dendrite_source[:chunk_size])
        for idx in range(chunk_size, len(dendrite_source), chunk_size):
            dendrite.append(dendrite_source[idx:idx + chunk_size])

        create_from_data(axon, dendrite, properties, f"file://{temp_dir}", 25)
        verify_precomputed_file(temp_dir, 25, 63803)

        create_from_data(axon, None, properties, f"file://{temp_dir}", 35)
        verify_precomputed_file(temp_dir, 35, 55514)

        create_from_data(None, dendrite, properties, f"file://{temp_dir}", 45)
        verify_precomputed_file(temp_dir, 45, 63803 - 55514 + 1)

    finally:
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    test_create_incremental()
    test_incremental_chunked()
