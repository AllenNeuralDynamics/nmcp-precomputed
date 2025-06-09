import os
import pickle
from pathlib import Path

from nmcp import SegmentInfo, NmcpPropertyValues

_test_structure_1 = {"acronym": "mlf",
                     "graph_id": 1,
                     "graph_order": 1120,
                     "id": 62,
                     "name": "medial longitudinal fascicle",
                     "structure_id_path": [997, 1009, 967, 832, 62],
                     "structure_set_ids": [184527634, 691663206],
                     "rgb_triplet": [204, 204, 204]}

_test_structure_2 = {'acronym': 'DG-sg',
                     'graph_id': 1,
                     'graph_order': 476,
                     'id': 632,
                     'name': 'Dentate gyrus, granule cell layer',
                     'structure_id_path': [997, 8, 567, 688, 695, 1089, 1080, 726, 632],
                     'structure_set_ids': [184527634, 12, 691663206],
                     'rgb_triplet': [102, 168, 61]}

_test_structure_3 = {'acronym': 'SEZ',
                     'graph_id': 1,
                     'graph_order': 1295,
                     'id': 98,
                     'name': 'subependymal zone',
                     'structure_id_path': [997, 73, 81, 98],
                     'structure_set_ids': [10, 184527634, 691663206],
                     'rgb_triplet': [170, 170, 170]}

_properties_1 = NmcpPropertyValues(label="N001-609281", strain="unknown 1", soma_id=_test_structure_1["id"])
_properties_2 = NmcpPropertyValues(label="N002-609281", strain="unknown 2", soma_id=_test_structure_2["id"])
_properties_3 = NmcpPropertyValues(label="N003-609281", strain="unknown 3", soma_id=_test_structure_3["id"])


def test_segment_info():
    s = SegmentInfo()

    s.append(998, _properties_1)
    s.append(999, _properties_2)

    _validate_segment_info(s)


def test_segment_info_update():
    s = SegmentInfo()

    s.append(998, _properties_1)
    s.append(999, _properties_2)

    _validate_segment_info(s)

    # Should have no effect.
    s.append(998, _properties_1)
    s.append(999, _properties_2)

    _validate_segment_info(s)

    # Make changes
    s.append(999, _properties_3)

    info = s.as_dict()

    labels = info["inline"]["properties"][0]
    assert len(labels["values"]) == 2
    assert labels["values"][0] == "N001-609281"
    assert labels["values"][1] == "N003-609281"

    strains = info["inline"]["properties"][1]
    assert len(strains["values"]) == 2
    assert strains["values"][0] == "unknown 1"
    assert strains["values"][1] == "unknown 3"

    tags = info["inline"]["properties"][2]

    assert len(tags["values"]) == 2
    # Not in order of added because of arguments to numpy.unique in segment_info
    assert tags["values"][0] == [1]
    assert tags["values"][1] == [0]
    assert len(tags["tags"]) == 2
    assert tags["tags"][0] == _test_structure_3["acronym"]
    assert tags["tags"][1] == _test_structure_1["acronym"]
    assert len(tags["tag_descriptions"]) == 2
    assert tags["tag_descriptions"][0] == _test_structure_3["name"]
    assert tags["tag_descriptions"][1] == _test_structure_1["name"]


def test_segment_info_load_and_append():
    source = Path(__file__).parent.joinpath("fixtures").joinpath("segment_info.pickle")
    with open(source, "rb") as input_file:
        s = pickle.loads(input_file.read())

    assert s is not None

    _validate_segment_info(s)

    s.append(997, _properties_3)

    info = s.as_dict()

    ids = info["inline"]["ids"]

    assert len(ids) == 3
    assert ids[2] == "997"

    labels = info["inline"]["properties"][0]
    assert len(labels["values"]) == 3
    assert labels["values"][2] == "N003-609281"

    strains = info["inline"]["properties"][1]
    assert len(strains["values"]) == 3
    assert strains["values"][2] == "unknown 3"

    tags = info["inline"]["properties"][2]
    # Not in same order of added because of arguments to numpy.unique in segment_info
    new_index = 1
    assert len(tags["values"]) == 3
    assert tags["values"][2] == [new_index]
    assert len(tags["tags"]) == 3
    assert tags["tags"][new_index] == _test_structure_3["acronym"]
    assert len(tags["tag_descriptions"]) == 3
    assert tags["tag_descriptions"][new_index] == _test_structure_3["name"]


def test_segment_info_remove():
    source = Path(__file__).parent.joinpath("fixtures").joinpath("segment_info.pickle")
    with open(source, "rb") as input_file:
        s = pickle.loads(input_file.read())

    s.append(997, _properties_3)

    assert len(s.ids) == 3

    to_remove = s.ids[1]

    s.remove(to_remove)

    assert len(s.ids) == 2

    assert s.ids == [998, 997]
    assert s.labels.values == ["N001-609281", "N003-609281"]
    assert s.strains.values == ["unknown 1", "unknown 3"]
    assert s.tags.values == [_test_structure_1["acronym"], _test_structure_3["acronym"]]
    assert s.tags.descriptions == [_test_structure_1["name"], _test_structure_3["name"]]

    info = s.as_dict()

    tags = info["inline"]["properties"][2]
    # Not in the same order as original 's' due to arguments to numpy.unique in segment_info.
    assert tags["values"][0] == [1]
    assert tags["values"][1] == [0]
    assert tags["tags"][0] == _test_structure_3["acronym"]
    assert tags["tags"][1] == _test_structure_1["acronym"]
    assert tags["tag_descriptions"][0] == _test_structure_3["name"]
    assert tags["tag_descriptions"][1] == _test_structure_1["name"]


def _validate_segment_info(s: SegmentInfo):
    info = s.as_dict()

    assert info["@type"] == "neuroglancer_segment_properties"

    ids = info["inline"]["ids"]

    assert len(ids) == 2
    assert ids[0] == "998"
    assert ids[1] == "999"

    assert len(info["inline"]["properties"]) == 3

    labels = info["inline"]["properties"][0]

    assert labels["id"] == "label"
    assert labels["type"] == "label"
    assert labels["description"] == "filename"
    assert len(labels["values"]) == 2
    assert labels["values"][0] == "N001-609281"
    assert labels["values"][1] == "N002-609281"

    strains = info["inline"]["properties"][1]

    assert strains["id"] == "strain"
    assert strains["type"] == "string"
    assert strains["description"] == "mouse line used"
    assert len(strains["values"]) == 2
    assert strains["values"][0] == "unknown 1"
    assert strains["values"][1] == "unknown 2"

    tags = info["inline"]["properties"][2]

    assert tags["id"] == "tags"
    assert tags["type"] == "tags"
    assert len(tags["values"]) == 2
    # Not in the same order as original 's' due to arguments to numpy.unique in segment_info.
    assert tags["values"][0] == [1]
    assert tags["values"][1] == [0]
    assert len(tags["tags"]) == 2
    assert tags["tags"][0] == _test_structure_2["acronym"]
    assert tags["tags"][1] == _test_structure_1["acronym"]
    assert len(tags["tag_descriptions"]) == 2
    assert tags["tag_descriptions"][0] == _test_structure_2["name"]
    assert tags["tag_descriptions"][1] == _test_structure_1["name"]
