import numpy

from allensdk.core.mouse_connectivity_cache import MouseConnectivityCache

from .segment_property import SegmentProperty

_structure_id_lookup = None

_acronym_not_found = "none"

_name_not_found = "none"


class SegmentTagProperty(SegmentProperty):
    def __init__(self, prop_id: str):
        super().__init__(prop_id, "tags")

        self.descriptions = list()

        self.tags = None
        self.tag_descriptions = None

    def append_tag(self, tag: str, tag_description: object):
        super(SegmentTagProperty, self).append(tag)

        self.descriptions.append(tag_description)

    def update_tag(self, index: int, tag: str, tag_description: object):
        super(SegmentTagProperty, self).update(index, tag)

        self.descriptions[index] = tag_description

    def as_dict(self) -> dict:
        property_desc = super(SegmentTagProperty, self).as_dict()

        if self.tags is not None:
            property_desc["tags"] = self.tags

        if self.tag_descriptions is not None:
            property_desc["tag_descriptions"] = self.tag_descriptions

        return property_desc

    def _create_export_values(self) -> list:
        unique_tags, unique_ref, tag_ref = numpy.unique(self.values, return_index=True, return_inverse=True)

        self.tags = unique_tags.tolist()

        if len(self.descriptions) > 0:
            self.tag_descriptions = [s for s in numpy.array(self.descriptions)[unique_ref]]

        return [[t] for t in tag_ref]


class SomaSegmentTagProperty(SegmentTagProperty):
    def __init__(self, prop_id: str):
        super().__init__(prop_id)

    def append_soma(self, soma_id: int | None):
        self.append_tag(*_use_soma_lookup(soma_id))

    def update_soma(self, index: int, soma_id: int | None):
        self.update_tag(index, *_use_soma_lookup(soma_id))


def _use_soma_lookup(soma_id: int | None) -> (str, str):
    global _structure_id_lookup

    if soma_id is not None:
        if _structure_id_lookup is None:
            _structure_id_lookup = MouseConnectivityCache(resolution=10).get_structure_tree()
        structure = _structure_id_lookup.get_structures_by_id([soma_id])[0]
        if structure is not None:
            return structure["acronym"], structure["name"]

    return _acronym_not_found, _name_not_found
