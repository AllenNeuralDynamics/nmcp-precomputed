import importlib.metadata
import logging
import os
import threading
from typing import cast

import uvicorn
from fastapi import FastAPI

from .models import ErrorKind, SkeletonRequest, SkeletonResponse, SkeletonResult
from .output_location import parse_output_location
from ..data.portal_reconstruction import PortalReconstruction
from ..precomputed import create_standalone_from_reconstruction, default_cloudvolume_info

logger = logging.getLogger(__name__)

_SERVICE_NAME = "NMCP Precomputed API"

_SERVICE_VERSION = importlib.metadata.version("nmcp-precomputed")


def create_app(worker_output: str) -> FastAPI:
    protected = parse_output_location(worker_output, require_protocol=False)

    generation_lock = threading.Lock()

    app = FastAPI(title=_SERVICE_NAME)

    @app.get("/")
    def read_root() -> str:
        return _SERVICE_NAME

    # A plain `def`, so FastAPI runs the blocking generation in its threadpool rather than on the event loop.
    @app.post("/generateskeleton")
    def generate_skeleton(request: SkeletonRequest) -> SkeletonResponse:
        reconstruction_id = request.reconstruction.id

        def response(**kwargs) -> SkeletonResponse:
            return SkeletonResponse(service_version=_SERVICE_VERSION, reconstruction_id=reconstruction_id, **kwargs)

        logger.info(f"received on-demand skeleton request for reconstruction {reconstruction_id} "
                    f"({len(request.reconstruction.nodes)} nodes, segment {request.segment_id}) at "
                    f"'{request.location}'")

        try:
            location = parse_output_location(request.location)
        except ValueError as ex:
            logger.warning(f"rejected on-demand skeleton for reconstruction {reconstruction_id}: invalid output "
                           f"location '{request.location}': {ex}")
            return response(error_kind=ErrorKind.INVALID_LOCATION,
                            error_description=f"Invalid output location for reconstruction {reconstruction_id}",
                            error_info=str(ex))

        if location.is_at_or_under(protected):
            logger.warning(f"rejected on-demand skeleton for reconstruction {reconstruction_id} at "
                           f"{location.cloudpath}: at or under the worker output {protected.cloudpath}")
            return response(error_kind=ErrorKind.PROTECTED_LOCATION,
                            error_description=f"The output location for reconstruction {reconstruction_id} is at "
                                              f"or under the worker's output location",
                            error_info=location.cloudpath)

        # Chosen here so an optional request argument can replace it without touching the generation code.
        dataset_info = default_cloudvolume_info()

        reconstruction = cast(PortalReconstruction, request.reconstruction.model_dump(by_alias=True))

        try:
            with generation_lock:
                skeleton = create_standalone_from_reconstruction(reconstruction, location.cloudpath,
                                                                 request.segment_id, cloud_files_info=dataset_info)
        except Exception as ex:
            logger.exception(f"failed to generate on-demand skeleton for reconstruction {reconstruction_id} at "
                             f"{location.cloudpath}")
            return response(error_kind=ErrorKind.GENERATION_ERROR,
                            error_description=f"Error generating precomputed skeleton for reconstruction "
                                              f"{reconstruction_id}",
                            error_info=f"{type(ex).__name__}: {ex}")

        logger.info(f"generated on-demand skeleton {request.segment_id} for reconstruction {reconstruction_id} at "
                    f"{location.cloudpath}")

        return response(result=SkeletonResult(location=location.cloudpath, segment_id=request.segment_id,
                                              node_count=len(skeleton.vertices), edge_count=len(skeleton.edges)))

    return app


def serve(app: FastAPI) -> None:
    uvicorn.run(app, host=os.environ.get("NMCP_PRECOMPUTED_API_HOST", "0.0.0.0"),
                port=int(os.environ.get("NMCP_PRECOMPUTED_API_PORT", "5000")), access_log=False)
