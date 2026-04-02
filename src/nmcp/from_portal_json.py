import argparse
import glob
import logging
import os.path
import sys

from .precomputed import create_from_json_files, NeuronStructure

logging.basicConfig(level=logging.INFO)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("input", help="the input json file")
    parser.add_argument("output", help="the output cloud volume location")

    args = parser.parse_args()

    if os.path.isdir(args.input):
        input_files = glob.glob(f"{args.input}/*.json")
    else:
        input_files = [args.input]

    skeleton_ids = create_from_json_files(input_files, f"{args.output}/full")
    print(skeleton_ids)
    skeleton_ids = create_from_json_files(input_files, f"{args.output}/axon", structure=NeuronStructure.AXON)
    print(skeleton_ids)
    skeleton_ids = create_from_json_files(input_files, f"{args.output}/dendrite", structure=NeuronStructure.DENDRITE)
    print(skeleton_ids)

    return True


if __name__ == '__main__':
    if main():
        sys.exit(0)
    else:
        sys.exit(1)
