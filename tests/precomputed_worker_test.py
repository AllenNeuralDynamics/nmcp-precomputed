import argparse
import logging

from nmcp import RemoteDataClient, create_from_data

logging.basicConfig(level=logging.WARNING)
logging.getLogger("nmcp").setLevel(logging.DEBUG)
logging.getLogger(__name__).setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)


def process(client: RemoteDataClient, output: str):

    try:
        data = client.get_reconstruction_data("8e682baf-ee5a-4fc0-b811-b5c63c652785")
        if data is not None:
            skeleton_id = create_from_data(data, f"{output}")
            logger.info(f"with skeleton id {skeleton_id} successfully processed")
    except Exception as ex:
        logger.error("process error", None, ex, True)


def main(url: str, auth_key: str, output: str):
    client = RemoteDataClient(url, auth_key)

    process(client, output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument("-u", "--url", help="URL of the GraphQL service")
    parser.add_argument("-a", "--authkey", help="authorization header for GraphQL service")
    parser.add_argument("-o", "--output", help="the output cloud volume location")

    args = parser.parse_args()

    main(args.url, args.authkey, args.output)
