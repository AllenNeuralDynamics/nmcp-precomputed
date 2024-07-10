from .segment_tag_property import SomaSegmentTagProperty
from .segment_property import SegmentProperty


class SegmentInfo:
    def __init__(self):
        self.ids = list()
        self.labels = SegmentProperty("label", "label", "filename")
        self.strains = SegmentProperty("strain", "string", "mouse line used")
        self.tags = SomaSegmentTagProperty("tags")

    def append(self, segment_id: int, label: str, strain: str, soma_id: int):
        if segment_id not in self.ids:
            self.ids.append(segment_id)
            self.labels.append(label)
            self.strains.append(strain)
            self.tags.append_soma(soma_id)
            return

        index = self.ids.index(segment_id)
        self.labels.update(index, label)
        self.strains.update(index, strain)
        self.tags.update_soma(index, soma_id)

    def as_dict(self) -> dict:
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
