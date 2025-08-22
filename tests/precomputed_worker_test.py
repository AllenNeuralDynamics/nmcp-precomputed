import argparse
import logging

from nmcp import RemoteDataClient, create_from_dict

logging.basicConfig(level=logging.WARNING)
logging.getLogger("nmcp").setLevel(logging.DEBUG)
logging.getLogger(__name__).setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)


def process(client: RemoteDataClient, output: str, reconstruction: str):
    try:
        data = client.get_reconstruction_data(reconstruction)
        if data is not None:
            skeleton_id = create_from_dict(data, output)
            logger.info(f"with skeleton id {skeleton_id} successfully processed")
    except Exception as ex:
        logger.error("process error", None, ex, True)


def main(url: str, auth_key: str, output: str, reconstruction: str):
    client = RemoteDataClient(url, auth_key)

    process(client, output, reconstruction)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument("-u", "--url", help="URL of the GraphQL service")
    parser.add_argument("-a", "--authkey", help="authorization header for GraphQL service")
    parser.add_argument("-o", "--output", help="the output cloud volume location")
    parser.add_argument("-r", "--reconstruction", help="id of the reconstruction to process")

    args = parser.parse_args()

    main(args.url, args.authkey, args.output, args.reconstruction)
