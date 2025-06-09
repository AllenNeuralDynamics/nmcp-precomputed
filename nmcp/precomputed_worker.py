import argparse
import logging
import threading

from nmcp import RemoteDataClient, create_from_data
from precomputed.nmcp_skeleton import ReconstructionType

logging.basicConfig(level=logging.WARNING)
logging.getLogger("nmcp").setLevel(logging.DEBUG)
logging.getLogger(__name__).setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)

process_interval: int = 10  # seconds
heartbeat_interval: int = 3600  # seconds

heartbeat_count_limit: int = int(heartbeat_interval / process_interval)
heartbeat_current_count: int = 0


def process_pending(client: RemoteDataClient, output: str):
    global heartbeat_current_count, heartbeat_count_limit

    try:
        pending = client.find_pending()

        if len(pending) > 0:
            logger.info(f"{len(pending)} pending precomputed entries")

            precomputed_id = None
            reconstruction_id = None
            skeleton_id = None
            data = None

            for pend in pending:
                data = client.get_reconstruction_data(pend.reconstructionId)
                if data is not None:
                    precomputed_id = pend.id
                    reconstruction_id = pend.reconstructionId
                    skeleton_id = pend.skeletonSegmentId
                    break

            if data is not None:
                logger.info(f"{reconstruction_id} with skeleton id {skeleton_id} has data available")

                # Create the full reconstruction.
                create_from_data(data, f"{output}/full", skeleton_id)

                # Create axon and dendrite.
                create_from_data(data, f"{output}/axon", skeleton_id,
                                 ReconstructionType.AXON)
                create_from_data(data, f"{output}/dendrite", skeleton_id,
                                 ReconstructionType.DENDRITE)

                if skeleton_id is not None:
                    logger.info(f"{reconstruction_id} with skeleton id {skeleton_id} successfully processed")
                    client.mark_generated(precomputed_id)
            else:
                logger.info("no pending reconstruction with data available")

            heartbeat_current_count = 0
        else:
            heartbeat_current_count += 1
            if heartbeat_current_count >= heartbeat_count_limit:
                logger.info("There are no pending precomputed entries")
                heartbeat_current_count = 0
    except Exception as ex:
        logger.error("process error", None, ex, True)

    t1 = threading.Timer(process_interval, process_pending, (client, output))
    t1.start()


def main(url: str, auth_key: str, output: str):
    logger.info(f"starting data client for url: {url}")
    logger.info(f"output base url: {output}")
    client = RemoteDataClient(url, auth_key)

    process_pending(client, output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument("-u", "--url", help="URL of the GraphQL service")
    parser.add_argument("-a", "--authkey", help="authorization header for GraphQL service")
    parser.add_argument("-o", "--output", help="the output cloud volume location")

    args = parser.parse_args()

    main(args.url, args.authkey, args.output)
