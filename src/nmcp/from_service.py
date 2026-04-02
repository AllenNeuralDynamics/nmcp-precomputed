import argparse
import logging

from .precomputed import create_from_reconstruction
from .data import RemoteDataClient
from .precomputed import NeuronStructure

logging.basicConfig(level=logging.WARNING)


def process_specimen_pending(client: RemoteDataClient, output_location: str):
    pending = client.find_specimen_space_pending()

    print(pending)

    for pend in pending:
        data = client.get_exported_specimen_space_reconstruction_data(pend.reconstructionId)

        skeleton_id = create_from_reconstruction(data, f"{output_location}/specimen", pend.skeletonId)
        print(skeleton_id)


def process_atlas_pending(client: RemoteDataClient, output_location: str):
    pending = client.find_atlas_pending()

    print(pending)

    for pend in pending:
        data = client.get_exported_atlas_space_reconstruction_data(pend.reconstructionId)

        skeleton_id = create_from_reconstruction(data, f"{output_location}/full", pend.skeletonId)
        print(skeleton_id)

        skeleton_id = create_from_reconstruction(data, f"{output_location}/axon", pend.skeletonId, NeuronStructure.AXON)
        print(skeleton_id)

        skeleton_id = create_from_reconstruction(data, f"{output_location}/dendrite", pend.skeletonId,
                                                 NeuronStructure.DENDRITE)
        print(skeleton_id)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("-o", "--output", help="the output cloud volume location")
    parser.add_argument("-u", "--url", help="URL of the GraphQL service")
    parser.add_argument("-a", "--authkey", help="authorization header for GraphQL service")

    args = parser.parse_args()

    client = RemoteDataClient(args.url, args.authkey)

    process_specimen_pending(client, args.output)

    process_atlas_pending(client, args.output)


if __name__ == "__main__":
    main()
