class SegmentProperty:
    def __init__(self, prop_id: str, prop_type: str, description: str = None, values=None):
        self.id = prop_id
        self.type = prop_type
        self.description = description
        self.values = values or list()

    def append(self, value) -> None:
        self.values.append(value)

    def remove(self, index: int) -> None:
        if index < len(self.values):
            del self.values[index]

    def update(self, index, value):
        if index < len(self.values):
            self.values[index] = value

    def as_dict(self) -> dict:
        property_desc = {
            "id": self.id,
            "type": self.type
        }

        if self.description is not None:
            property_desc["description"] = self.description

        property_desc["values"] = self._create_export_values()

        return property_desc

    def _create_export_values(self) -> list:
        return self.values
