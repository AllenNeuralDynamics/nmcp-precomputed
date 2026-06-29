import logging

from .api import create_app, serve
from .api.output_location import parse_output_location
from .precomputed import load_structure_tree
from .precomputed_worker import start

logger = logging.getLogger(__name__)


def run(url: str, auth_key: str, output: str) -> None:
    """
    Run the polling worker and the on-demand API in this process. The order matters: nothing is scheduled or served
    until the output location is validated and the structure tree is loaded, so the worker never holds the tree's
    initialization lock while an API request waits on it.
    """
    worker_output = parse_output_location(output, require_protocol=False).cloudpath

    if worker_output != output.strip():
        logger.warning(f"the configured output location '{output}' is not normalized; the worker writes to "
                       f"'{worker_output}'")

    app = create_app(worker_output)

    try:
        load_structure_tree()
    except Exception:
        logger.exception("could not load the Allen structure tree; exiting so the container restarts")
        raise

    start(url, auth_key, worker_output)

    serve(app)
