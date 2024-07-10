from nmcp import SegmentProperty


def test_segment_property():
    prop = SegmentProperty("strain", "string", "filename")

    assert prop.id == "strain"
    assert prop.type == "string"
    assert prop.description == "filename"

    prop.append("A")
    prop.append("B")

    desc = prop.as_dict()

    assert desc["id"] == "strain"
    assert desc["type"] == "string"
    assert desc["description"] == "filename"

    values = desc["values"]

    assert len(values) == 2
    assert values[0] == "A"
    assert values[1] == "B"
