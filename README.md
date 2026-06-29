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
used in the `NMCP_PRECOMPUTED_OUTPUT` environment variable for `nmcp-client`.

## On-Demand API
In addition to polling, the service exposes an HTTP API that converts a posted portal-format reconstruction into a
complete, self-contained precomputed dataset (one Neuroglancer layer holding a single skeleton) at a location chosen by
the caller. It uses the same conversion as the worker, so the skeleton output is identical.

The API runs in the same process as the polling worker. API requests run concurrently with worker generations and never
wait for one to finish; they are serialized only with other API requests.

### Startup
`python -m nmcp` (and therefore `docker-entry.sh`) starts both. Before either runs, it:

1. validates and normalizes the worker output location (`-o`, required);
2. loads the Allen structure tree used for soma-location tags.

If either step fails, the process exits so the container restarts it. After the first successful load, the tree is
read from allensdk's `mouse_connectivity/` cache, so later restarts do not need network access.

The worker output location is normalized at startup: protocol-only (`s3://`, `gs://`, `file://` or a configured
cloud-files alias), with no trailing slash and no `precomputed://` prefix or `|precomputed:` suffix. The worker writes
under the normalized location, and a warning is logged when the configured value differed from it. Set
`NMCP_PRECOMPUTED_OUTPUT` in normalized form, because `nmcp-client` composes its own dataset paths (`<value>/full`, …)
from the same value and must read the same datasets the worker writes.

| Environment variable | Default | Purpose |
|---|---|---|
| `NMCP_PRECOMPUTED_API_HOST` | `0.0.0.0` | Interface the API listens on |
| `NMCP_PRECOMPUTED_API_PORT` | `5000` | Port the API listens on |

### Endpoints
`GET /` returns `"NMCP Precomputed API"`.

`POST /generateskeleton` takes the output location, an optional segment id (default `1`, range `1` to `2^64 - 1`) and
the reconstruction in the portal export format:

```json
{
  "location": "s3://bucket/path/to/dataset",
  "segmentId": 1,
  "reconstruction": {
    "id": "…",
    "neuron": {"label": "N004", "specimen": {"label": "648434", "genotype": "Dbh-Cre_KI"}},
    "nodes": [{"index": 1, "structure": 1, "x": 0.0, "y": 0.0, "z": 0.0, "radius": 1.0, "parentIndex": -1, "atlasStructure": 202}]
  }
}
```

It returns once the dataset is written:

```json
{
  "serviceVersion": "3.0.7",
  "reconstructionId": "…",
  "result": {"location": "s3://bucket/path/to/dataset", "segmentId": 1, "nodeCount": 9, "edgeCount": 8},
  "errorKind": null, "errorDescription": null, "errorInfo": null
}
```

Every request the service handles returns 200. On failure `result` is null and `errorKind` is one of:

- `InvalidLocation`: the location cannot be parsed, has no explicit protocol, or names a format other than
  precomputed.
- `ProtectedLocation`: the location is the worker's output location or lies under it. Locations are compared after
  resolving cloud-files aliases, trailing slashes, the precomputed prefix and suffix, and local symlinks.
- `GenerationError`: writing the dataset failed; `errorInfo` holds the exception type and message.

A body that fails validation (a missing field, a segment id of 0) gets FastAPI's standard 422 response.

The dataset is written over whatever already exists at the location without clearing it first. Skeleton files from
earlier calls with other segment ids remain, though the segment properties list only the latest segment.

### Running Locally
```bash
uv sync --extra numerics --extra api --extra test
uv run python -m nmcp -u <graphql-url> -a <key> -o <worker-output>
```

```bash
curl -s -X POST localhost:5000/generateskeleton -H "Content-Type: application/json" -d @body.json
```
