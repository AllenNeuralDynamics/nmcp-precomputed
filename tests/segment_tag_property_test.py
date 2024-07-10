from nmcp import SegmentTagProperty, SomaSegmentTagProperty


def test_segment_tag_property():
    prop = SegmentTagProperty("my_tags")

    assert prop.id == "my_tags"
    assert prop.type == "tags"
    assert prop.description is None

    descriptions = [{
        "name": "D1",
        "acronym": "D1A",
    }, {
        "name": "D2",
        "acronym": "D2A",
    }, {
        "name": "D3",
        "acronym": "D3A",
    }]

    prop.append_tag("A", descriptions[0])
    prop.append_tag("B", descriptions[1])
    prop.append_tag("A", descriptions[0])

    desc = prop.as_dict()

    assert desc["id"] == "my_tags"
    assert desc["type"] == "tags"
    assert "description" not in desc

    values = desc["values"]

    assert len(values) == 3
    assert values[0] == [0]
    assert values[1] == [1]
    assert values[2] == [0]

    tags = desc["tags"]

    assert len(tags) == 2
    assert tags[0] == "A"
    assert tags[1] == "B"

    tag_descriptions = desc["tag_descriptions"]

    assert len(tag_descriptions) == 2
    assert tag_descriptions[0] == descriptions[0]
    assert tag_descriptions[1] == descriptions[1]


def test_soma_segment_tag_property():
    prop = SomaSegmentTagProperty("my_tags")

    prop.append_soma(319)
    prop.append_soma(703)
    prop.append_soma(319)
    prop.append_soma(100000)

    desc = prop.as_dict()

    tags = desc["tags"]

    assert len(tags) == 3
    assert tags[0] == "BMA"
    assert tags[1] == "CTXsp"
    assert tags[2] == "none"

    tag_descriptions = desc["tag_descriptions"]

    assert len(tag_descriptions) == 3
    assert tag_descriptions[0] == "Basomedial amygdalar nucleus"
    assert tag_descriptions[1] == "Cortical subplate"
    assert tag_descriptions[2] == "none"
