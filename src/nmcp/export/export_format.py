from enum import IntEnum


class ExportFormat(IntEnum):
    """
    Export formats supported by the NMCP Export Service.  This is not directly relevant to Neuroglancer Precomputed
    Skeleton generation, but may be relevant when acquiring related assets.
    """
    SWC = 100
    PORTAL_JSON = 300
    LEGACY_JSON = 900
