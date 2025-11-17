from cloudvolume import CloudVolume

info = CloudVolume.create_new_info(
        num_channels=1,
        layer_type="segmentation",
        data_type="uint64",  # Channel images might be "uint8"
        # raw, png, jpeg, compressed_segmentation, fpzip, compressed, zfpc, compresso, crackle
        encoding="raw",
        resolution=[1000, 1000, 1000],  # Voxel scaling, units are in nanometers
        voxel_offset=[0, 0, 0],  # x,y,z offset in voxels from the origin
        # mesh="mesh",
        skeletons="skeleton",
        # Pick a convenient size for your underlying chunk representation
        # Powers of two are recommended, doesn't need to cover image exactly
        chunk_size=[512, 512, 512],  # units are voxels
        volume_size=[13200, 8000, 11400],  # e.g. a cubic millimeter dataset
    )

cv = CloudVolume("minio://aind-neuron-morphology-community-portal-local/ngv01/full", info=info, compress=False)

cv.commit_info()
