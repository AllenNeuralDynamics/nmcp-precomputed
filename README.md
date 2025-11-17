# NMCP Precomputed
The NMCP Precomputed service generates reconstruction skeletons in Neuroglancer's precomputed format.  It periodically
polls the API service for reconstructions that are ready for new or updated skeletons.

Given the current behavior or Neuroglancer layers and the NMCP viewer feature requirements, the service currently
generated separate data sources for the full reconstruction, as well as axon-only and dendrite-only versions.

The service uses the chunked API for acquiring reconstruction data and should be compatible with dense reconstruction
sources.

## Local Development
A local S3-compatible service may be used during local development to avoid AWS or other cloud service storage charges.

_Note that at this time, cloud-files only appears to support this option from Linux, WSL, or MacOS._

One functional option is to run a local [MinIO](https://www.min.io/) Docker container.  The following steps describe the
process (and assume the default configuration of port 9000 for MinIO).  For additional details see either the MinIO
documentation, [cloud-files](https://github.com/seung-lab/cloud-files), and 
[cloud-volume](https://github.com/seung-lab/cloud-volume).

* Install the MinIO command line tool, `mc`
* Use `mc` or the web interface at http://localhost:9001 to create a bucket
* Use `mc` to set the bucket to public access (this portion is for Neuroglancer viewing, not required for precomputed generation)
* With the Python environment for this project active (which should mean the cloud-files command line interface is available):
  * Add an alias for your instance: `cloudfiles alias add minio s3://http://127.0.0.1:9000/`
* When running the precomputed worker, pass the alias as the precomputed output argument, _e.g._,
  * `-o minio://<your_bucket>/ngv01`

Here the current standard path is used as the base location (`ngv01`), however anything can used so long as it is also
used in the `NMCP_PRECOMPUTED` environment variable for `nmcp-client`.
