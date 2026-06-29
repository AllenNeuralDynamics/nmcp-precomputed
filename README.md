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

A preconfigured instance is defined in `docker-compose.yml` that can be started with the following script

```bash
docker compose -p nmcp up -d
```

Attach to the running container to configure the precomputed bucket.

Find the container id
```bash
docker ps
```

Attach to the instance
```bash
docker exec -it <container-id> /bin/bash
```

Define an `mc` alias for the server, create the bucket, and allow public access for the Neuroglancer viewer.  The 
following assumes the username/password defined in `docker-compose.yml`.  This is performed in the container after
attaching above, not on the host (unless you choose to install the `mc` tools on your host machine).
```bash
mc alias set myminio http://localhost:9000 root password
mc mb myminio/aind-neuron-morphology-community-portal-local/ngv01/
mc anonymous set public myminio/aind-neuron-morphology-community-portal-local/ngv01
```

Exit the container instance.  On the host (in the Python environment created for this project w/cloud-files installed),
create an alias for the server.

```bash
cloudfiles alias add minio s3://http://127.0.0.1:9000/
```

Add the username and password as a secrets file in `~/.cloudvolume/secrets/minio-secret.json` (assumes defaults used
in the compose file).
```json
{
	"AWS_ACCESS_KEY_ID": "root",
	"AWS_SECRET_ACCESS_KEY": "password"
}
```

Although the bucket is set for public access in this development example, adding the authentication when generating
the precomputed data mimics the typical behavior in actual deployments.

When running the precomputed worker, pass the alias as the precomputed output argument, _e.g._, `-o minio://aind-neuron-morphology-community-portal-local/ngv01`

Here the current standard path is used as the base location (`ngv01`), however anything can used so long as it is also
used in the `NMCP_PRECOMPUTED` environment variable for `nmcp-client`.
