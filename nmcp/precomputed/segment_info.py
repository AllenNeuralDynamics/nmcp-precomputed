from typing import NamedTuple

from .segment_tag_property import SomaSegmentTagProperty
from .segment_property import SegmentProperty


class NmcpPropertyValues(NamedTuple):
    label: str
    strain: str
    soma_id: int


class SegmentInfo:
    """
    Create, update, and persist the `segment_properties` `info` file for Neuroglancer precomputed datasets with
    properties specific to the NMCP reconstruction skeletons.  It is intended to support datasets that change over time,
    including the addition of new skeletons, the modification of existing skeletons, and removal of existing skeletons.
    """

    def __init__(self):
        self.ids = list()
        self.labels = SegmentProperty("label", "label", "filename")
        self.strains = SegmentProperty("strain", "string", "mouse line used")
        self.tags = SomaSegmentTagProperty("tags")

    def append(self, segment_id: int, values: NmcpPropertyValues):
        if segment_id not in self.ids:
            self.ids.append(segment_id)
            self.labels.append(values.label)
            self.strains.append(values.strain)
            self.tags.append_soma(values.soma_id)
            return

        index = self.ids.index(segment_id)
        self.labels.update(index, values.label)
        self.strains.update(index, values.strain)
        self.tags.update_soma(index, values.soma_id)

    def remove(self, segment_id: int):
        if segment_id in self.ids:
            index = self.ids.index(segment_id)
            del self.ids[index]
            self.labels.remove(index)
            self.strains.remove(index)
            self.tags.remove_soma(index)

    def as_dict(self) -> dict:
        """
        Generates a JSON-serializable dictionary representation suitable for the `segment_properties/info` file.
        """
        return {
            "@type": "neuroglancer_segment_properties",
            "inline": {
                "ids": [f'{s}' for s in self.ids],
                "properties": [
                    self.labels.as_dict(),
                    self.strains.as_dict(),
                    self.tags.as_dict(),
                ]
            }
        }
