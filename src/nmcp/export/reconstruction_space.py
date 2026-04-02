from enum import IntEnum


class ReconstructionSpace(IntEnum):
    """
    Reconstruction coordinate spaces supported by the NMCP Export Service.  This is not directly relevant to
    Neuroglancer Precomputed Skeleton generation, but may be relevant when acquiring related assets.
    """
    SPECIMEN = 100
    ATLAS = 200
