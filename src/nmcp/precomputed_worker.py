import argparse
import logging
import threading

from .data import RemoteDataClient, PrecomputedEntry
from .precomputed import ensure_bucket_folders, create_from_data, extract_neuron_properties, SkeletonComponents

logging.basicConfig(level=logging.WARNING)
logging.getLogger("nmcp").setLevel(logging.DEBUG)
logging.getLogger(__name__).setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)

process_interval: int = 10  # seconds
heartbeat_interval: int = 3600  # seconds

heartbeat_count_limit: int = int(heartbeat_interval / process_interval)
heartbeat_current_count: int = 0


def load_specimen_space_reconstruction(client: RemoteDataClient, pending: PrecomputedEntry):
    reconstruction_id = pending.reconstructionId
    skeleton_id = pending.skeletonId

    data = client.get_specimen_space_reconstruction_data(reconstruction_id)

    try:
        # Extract properties once from header
        properties = extract_neuron_properties(data)

        axon_components = SkeletonComponents.create(data["axon"])

        dendrite_components = SkeletonComponents.create(data["dendrite"])

        return axon_components, dendrite_components, properties

    except Exception as ex:
        logger.error(f"error loading specimen space reconstruction {reconstruction_id}: {ex}")
        return None


def load_reconstruction(client: RemoteDataClient, pending: PrecomputedEntry):
    header_data = client.get_reconstruction_header(pending.reconstructionId)

    reconstruction_id = pending.reconstructionId
    skeleton_id = pending.skeletonId

    if header_data is None or reconstruction_id is None or skeleton_id is None:
        return None

    logger.info(f"{reconstruction_id} with skeleton id {skeleton_id} has header data available")

    try:
        # Extract properties once from header
        properties = extract_neuron_properties(header_data)

        # Process axon data in true chunks
        logger.info(f"retrieving axon data in chunks for {reconstruction_id}")
        axon_components = None
        chunk_size = 25000
        axon_offset = 0
        axon_total_points = 0

        while True:
            logger.debug(f"fetching axon chunk at offset {axon_offset} with size {chunk_size}")
            axon_result = client.get_axon_chunks(
                reconstruction_id,
                chunk_size=chunk_size,
                offset=axon_offset,
                limit=chunk_size
            )

            if not axon_result or not axon_result["data"]:
                logger.debug("no more axon data available")
                break

            chunk_points = axon_result["data"]
            chunk_count = len(chunk_points)

            if axon_components is None:
                # First chunk - create new SkeletonComponents
                logger.debug(f"creating axon components with {chunk_count} points")
                axon_components = SkeletonComponents.create(chunk_points)
            else:
                # Subsequent chunks - append to existing
                logger.debug(f"appending {chunk_count} points to axon components")
                axon_components.append(chunk_points)

            axon_total_points += chunk_count

            # Check if we got less than requested (end of data)
            if chunk_count < chunk_size:
                logger.debug(f"received {chunk_count} < {chunk_size}, end of axon data")
                break

            axon_offset += chunk_count

        if axon_components is not None:
            logger.info(f"assembled axon with {axon_total_points} total points")

        # Process dendrite data in true chunks
        logger.info(f"retrieving dendrite data in chunks for {reconstruction_id}")
        dendrite_components = None

        dendrite_offset = 0
        dendrite_total_points = 0

        while True:
            logger.debug(f"fetching dendrite chunk at offset {dendrite_offset} with size {chunk_size}")
            dendrite_result = client.get_dendrite_chunks(
                reconstruction_id,
                chunk_size=chunk_size,
                offset=dendrite_offset,
                limit=chunk_size
            )

            if not dendrite_result or not dendrite_result["data"]:
                logger.debug("no more dendrite data available")
                break

            chunk_points = dendrite_result["data"]
            chunk_count = len(chunk_points)

            if dendrite_components is None:
                # First chunk - create new SkeletonComponents
                logger.debug(f"creating dendrite components with {chunk_count} points")
                dendrite_components = SkeletonComponents.create(chunk_points)
            else:
                # Subsequent chunks - append to existing
                logger.debug(f"appending {chunk_count} points to dendrite components")
                dendrite_components.append(chunk_points)

            dendrite_total_points += chunk_count

            # Check if we got less than requested (end of data)
            if chunk_count < chunk_size:
                logger.debug(f"received {chunk_count} < {chunk_size}, end of dendrite data")
                break

            dendrite_offset += chunk_count

        if dendrite_components is not None:
            logger.info(f"assembled dendrite with {dendrite_total_points} total points")

        return axon_components, dendrite_components, properties

    except Exception as ex:
        logger.error(f"error loading reconstruction {reconstruction_id}: {ex}")
        return None


def save_specimen_precomputed(output, skeleton_id, properties, axon_components, dendrite_components):
    logger.info(f"creating specimen space precomputed skeleton {skeleton_id}")
    create_from_data(axon_components, dendrite_components, properties, f"{output}/specimen", skeleton_id)


def save_atlas_precomputed(output, skeleton_id, properties, axon_components, dendrite_components):
    # Create the full reconstruction (both axon and dendrite)
    logger.info(f"creating full reconstruction for skeleton {skeleton_id}")
    create_from_data(axon_components, dendrite_components, properties, f"{output}/full", skeleton_id)

    # Create axon-only reconstruction
    logger.info(f"creating axon-only reconstruction for skeleton {skeleton_id}")
    create_from_data(axon_components, None, properties, f"{output}/axon", skeleton_id)

    # Create dendrite-only reconstruction
    logger.info(f"creating dendrite-only reconstruction for skeleton {skeleton_id}")
    create_from_data(None, dendrite_components, properties, f"{output}/dendrite", skeleton_id)


def process_pending(client: RemoteDataClient, output: str):
    global heartbeat_current_count, heartbeat_count_limit

    processed_atlas = process_atlas_pending(client, output)
    processed_specimen = process_specimen_pending(client, output)

    if processed_atlas or processed_specimen:
        heartbeat_current_count = 0
    else:
        heartbeat_current_count += 1
        if heartbeat_current_count >= heartbeat_count_limit:
            logger.info("There are no pending precomputed entries")
            heartbeat_current_count = 0

    t1 = threading.Timer(process_interval, process_pending, (client, output))
    t1.start()


def process_specimen_pending(client: RemoteDataClient, output: str) -> bool:
    try:
        pending = client.find_specimen_space_pending()

        if len(pending) > 0:
            logger.info(f"{len(pending)} pending specimen space precomputed entries")

            for pend in pending:
                try:
                    reconstruction = load_specimen_space_reconstruction(client, pend)

                    if reconstruction is None:
                        client.mark_specimen_failed_load(pend.id)
                        continue

                    axon_components, dendrite_components, properties = reconstruction

                    save_specimen_precomputed(output, pend.skeletonId, properties, axon_components,
                                              dendrite_components)

                    client.mark_specimen_generated(pend.id)
                except Exception as ex:
                    logger.error("error", None, ex, True)
                    client.mark_specimen_failed_generate(pend.id)

            return True
    except Exception as ex:
        logger.error("process error", None, ex, True)

    return False


def process_atlas_pending(client: RemoteDataClient, output: str) -> bool:
    try:
        pending = client.find_atlas_pending()

        if len(pending) > 0:
            logger.info(f"{len(pending)} pending atlas precomputed entries")

            for pend in pending:
                try:
                    reconstruction = load_reconstruction(client, pend)

                    if reconstruction is None:
                        client.mark_atlas_failed_load(pend.id)
                        continue

                    axon_components, dendrite_components, properties = reconstruction

                    save_atlas_precomputed(output, pend.skeletonId, properties, axon_components,
                                           dendrite_components)

                    client.mark_atlas_generated(pend.id)
                except Exception as ex:
                    logger.error("error", None, ex, True)
                    client.mark_atlas_failed_generate(pend.id)

            return True
    except Exception as ex:
        logger.error("process error", None, ex, True)

    return False


def main(url: str, auth_key: str, output: str):
    logger.info(f"starting data client for url: {url}")
    logger.info(f"output base url: {output}")

    ensure_bucket_folders(output)

    client = RemoteDataClient(url, auth_key)

    process_pending(client, output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument("-u", "--url", help="URL of the GraphQL service")
    parser.add_argument("-a", "--authkey", help="authorization header for GraphQL service")
    parser.add_argument("-o", "--output", help="the output cloud volume location")

    args = parser.parse_args()

    main(args.url, args.authkey, args.output)
