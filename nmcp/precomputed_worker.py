import argparse
import logging
import threading

from nmcp import RemoteDataClient, create_from_dict

logging.basicConfig(level=logging.WARNING)
logging.getLogger("nmcp").setLevel(logging.DEBUG)
logging.getLogger(__name__).setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)


def process_pending(client: RemoteDataClient, output: str):
    try:
        pending = client.find_pending()

        logger.info(f"{len(pending)} pending precomputed entries")

        if len(pending) > 0:
            reconstructions = list()

            for pend in pending:
                data = client.get_reconstruction_data(pend.reconstructionId)
                if data is not None:
                    data["skeleton_id"] = pend.skeletonSegmentId
                    reconstructions.append(data)

            logger.info(f"{len(reconstructions)} reconstructions with data available")

            ids = create_from_dict(reconstructions, output)

            logger.info(f"{len(ids)} successfully processed")

            for pend in pending:
                if pend.skeletonSegmentId in ids:
                    client.mark_generated(pend)
    except Exception as ex:
        logger.error(ex)

    t1 = threading.Timer(30.0, process_pending, (client, output))
    t1.start()


def main(url: str, auth_key: str, output: str):
    client = RemoteDataClient(url, auth_key)

    process_pending(client, output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument("-u", "--url", help="URL of the GraphQL service")
    parser.add_argument("-a", "--authkey", help="authorization header for GraphQL service")
    parser.add_argument("-o", "--output", help="the output cloud volume location")

    args = parser.parse_args()

    main(args.url, args.authkey, args.output)
