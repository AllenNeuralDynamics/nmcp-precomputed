import logging
import threading

from gql.transport.exceptions import TransportConnectionFailed

from . import create_from_reconstruction
from .data import RemoteDataClient
from .data.portal_reconstruction import PortalReconstruction
from .precomputed import ensure_bucket_folders, NeuronStructure

logging.basicConfig(level=logging.WARNING)
logging.getLogger("nmcp").setLevel(logging.DEBUG)
logging.getLogger(__name__).setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)

process_interval: int = 10  # seconds
heartbeat_interval: int = 3600  # seconds

heartbeat_count_limit: int = int(heartbeat_interval / process_interval)
heartbeat_current_count: int = 0

graphql_unreachable: bool = False


def load_specimen_space_reconstruction(client: RemoteDataClient, reconstruction_id: str) -> PortalReconstruction | None:
    if reconstruction_id is None:
        return None

    reconstruction_data = client.get_exported_specimen_space_reconstruction_data(reconstruction_id)

    if reconstruction_data is None:
        return None

    return reconstruction_data


def load_atlas_reconstruction(client: RemoteDataClient, reconstruction_id: str) -> PortalReconstruction | None:
    if reconstruction_id is None:
        return None

    reconstruction_data = client.get_exported_atlas_space_reconstruction_data(reconstruction_id)

    if reconstruction_data is None:
        return None

    return reconstruction_data


def save_specimen_precomputed(skeleton_id: int, reconstruction: PortalReconstruction, output: str):
    logger.info(f"creating specimen space precomputed skeleton {skeleton_id}")
    create_from_reconstruction(reconstruction, f"{output}/specimen", skeleton_id)


def save_atlas_precomputed(skeleton_id: int, reconstruction: PortalReconstruction, output: str):
    # Create the full reconstruction (both axon and dendrite)
    logger.info(f"creating full reconstruction for skeleton {skeleton_id}")
    create_from_reconstruction(reconstruction, f"{output}/full", skeleton_id)

    # Create axon-only reconstruction
    logger.info(f"creating axon-only reconstruction for skeleton {skeleton_id}")
    create_from_reconstruction(reconstruction, f"{output}/axon", skeleton_id, NeuronStructure.AXON)

    # Create dendrite-only reconstruction
    logger.info(f"creating dendrite-only reconstruction for skeleton {skeleton_id}")
    create_from_reconstruction(reconstruction, f"{output}/dendrite", skeleton_id, NeuronStructure.DENDRITE)


def process_pending(client: RemoteDataClient, output_location: str):
    global heartbeat_current_count, heartbeat_count_limit

    processed_atlas = process_atlas_pending(client, output_location)

    processed_specimen = process_specimen_pending(client, output_location)

    if processed_atlas or processed_specimen:
        heartbeat_current_count = 0
    else:
        heartbeat_current_count += 1
        if heartbeat_current_count >= heartbeat_count_limit:
            logger.info("There are no pending precomputed entries")
            heartbeat_current_count = 0

    _schedule(client, output_location, process_interval)


def _schedule(client: RemoteDataClient, output_location: str, delay: float) -> None:
    timer = threading.Timer(delay, process_pending, (client, output_location))
    # Daemon, so the process exits when the API server stops; an interrupted cycle leaves its entries pending.
    timer.daemon = True
    timer.start()


def process_specimen_pending(client: RemoteDataClient, output_location: str) -> bool:
    try:
        pending = client.find_specimen_space_pending()

        _note_reachable()

        if len(pending) > 0:
            logger.info(f"{len(pending)} pending specimen space precomputed entries")

            for pend in pending:
                try:
                    reconstruction = load_specimen_space_reconstruction(client, pend.reconstructionId)

                    if reconstruction is None:
                        client.mark_specimen_failed_load(pend.id)
                        continue

                    save_specimen_precomputed(pend.skeletonId, reconstruction, output_location)

                    client.mark_specimen_generated(pend.id)
                except Exception:
                    logger.exception(f"failed to generate specimen space precomputed for entry {pend.id} "
                                     f"(skeleton {pend.skeletonId})")
                    client.mark_specimen_failed_generate(pend.id)

            return True
    except TransportConnectionFailed as ex:
        _note_unreachable(ex)
    except Exception:
        logger.exception("failed to process pending specimen space precomputed entries")

    return False


def process_atlas_pending(client: RemoteDataClient, output_location: str) -> bool:
    try:
        pending = client.find_atlas_pending()

        _note_reachable()

        if len(pending) > 0:
            logger.info(f"{len(pending)} pending atlas precomputed entries")

            for pend in pending:
                try:
                    reconstruction = load_atlas_reconstruction(client, pend.reconstructionId)

                    if reconstruction is None:
                        client.mark_atlas_failed_load(pend.id)
                        continue

                    save_atlas_precomputed(pend.skeletonId, reconstruction, output_location)

                    client.mark_atlas_generated(pend.id)
                except Exception:
                    logger.exception(f"failed to generate atlas precomputed for entry {pend.id} "
                                     f"(skeleton {pend.skeletonId})")
                    client.mark_atlas_failed_generate(pend.id)

            return True
    except TransportConnectionFailed as ex:
        _note_unreachable(ex)
    except Exception:
        logger.exception("failed to process pending atlas precomputed entries")

    return False


def start(url: str, auth_key: str, output: str):
    logger.info(f"starting data client for url: {url}")
    logger.info(f"output base url: {output}")

    ensure_bucket_folders(output)

    client = RemoteDataClient(url, auth_key)

    _schedule(client, output, 0)


def _note_unreachable(ex: TransportConnectionFailed) -> None:
    global graphql_unreachable

    # Logged once per outage: every cycle fails both queries, and a full traceback for each buries everything else.
    if not graphql_unreachable:
        logger.warning(f"the GraphQL service is unreachable; retrying every {process_interval} seconds: {ex}")

    graphql_unreachable = True


def _note_reachable() -> None:
    global graphql_unreachable

    if graphql_unreachable:
        logger.info("the GraphQL service is reachable again")

    graphql_unreachable = False
