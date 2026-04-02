from typing_extensions import NamedTuple

from .segment_tag_property import SomaSegmentTagProperty
from .segment_property import SegmentProperty


class SegmentPropertyValues(NamedTuple):
    label: str
    genotype: str
    soma_atlas_structure_id: int


class SegmentInfo:
    """
    Create, update, and persist the `segment_properties` `info` file for Neuroglancer precomputed datasets with
    properties specific to the NMCP reconstruction skeletons.  It is intended to support datasets that change over time,
    including the addition of new skeletons, the modification of existing skeletons, and removal of existing skeletons.
    """

    def __init__(self):
        self.ids = list()
        self.labels = SegmentProperty("label", "label", "neuron identifier")
        self.genotypes = SegmentProperty("genotype", "string", "animal genotype")
        self.tags = SomaSegmentTagProperty("tags")

    def append(self, segment_id: int, values: SegmentPropertyValues):
        if segment_id not in self.ids:
            self.ids.append(segment_id)
            self.labels.append(values.label)
            self.genotypes.append(values.genotype)
            self.tags.append_soma(values.soma_atlas_structure_id)
            return

        index = self.ids.index(segment_id)
        self.labels.update(index, values.label)
        self.genotypes.update(index, values.genotype)
        self.tags.update_soma(index, values.soma_atlas_structure_id)

    def remove(self, segment_id: int):
        if segment_id in self.ids:
            index = self.ids.index(segment_id)
            del self.ids[index]
            self.labels.remove(index)
            self.genotypes.remove(index)
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
                    self.genotypes.as_dict(),
                    self.tags.as_dict(),
                ]
            }
        }
