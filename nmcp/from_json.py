import argparse
import glob
import logging
import os.path
import sys

from nmcp import create_from_json_files

logging.basicConfig(level=logging.WARNING)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("input", help="the input json file")
    parser.add_argument("output", help="the output cloud volume location")

    args = parser.parse_args()

    if os.path.isdir(args.input):
        input_files = glob.glob(f"{args.input}/*.json")
    else:
        input_files = [args.input]

    create_from_json_files(input_files, args.output)

    return True


if __name__ == '__main__':
    if main():
        sys.exit(0)
    else:
        sys.exit(1)
