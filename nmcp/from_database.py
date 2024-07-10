import argparse
import logging

from nmcp import RemoteDataClient, create_from_dict

logging.basicConfig(level=logging.WARNING)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("-o", "--output", help="the output cloud volume location")
    parser.add_argument("-u", "--url", help="URL of the GraphQL service")
    parser.add_argument("-a", "--authkey", help="authorization header for GraphQL service")

    args = parser.parse_args()

    client = RemoteDataClient(args.url, args.authkey)

    pending = client.find_pending()

    print(pending)

    neurons = list()

    for pend in pending:
        data = client.get_reconstruction_data(pend.reconstructionId)
        data["skeleton_id"] = pend.skeletonSegmentId
        neurons.append(data)

    create_from_dict(neurons, args.output)


if __name__ == "__main__":
    main()
