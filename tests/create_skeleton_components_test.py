import json
import os

import numpy

from precomputed.nmcp_skeleton import create_skeleton_components, SkeletonComponents


def verify_contents(components: SkeletonComponents, size, compartment: int | None = None):
    assert components is not None

    assert components.vertices.shape == (size, 3)
    assert components.edges.shape == (size - 1, 2)
    assert components.radii.shape == (size,)
    assert components.compartments.shape == (size,)
    assert components.ccf_ids.shape == (size,)

    if compartment is not None:
        assert numpy.allclose(components.ccf_ids, compartment, atol=1e-6, rtol=1e-6)


def test_create_skeleton_components():
    json_file = os.path.abspath(os.path.join(os.path.dirname(__file__), 'fixtures', 'tiny.json'))

    with open(json_file) as f:
        data = json.load(f)

    axon, dendrite = create_skeleton_components(data["neurons"][0])

    verify_contents(axon, 3, 437)
    verify_contents(dendrite, 4, 445)

    output = axon.concat(dendrite)

    verify_contents(output, 6)


if __name__ == '__main__':
    test_create_skeleton_components()
