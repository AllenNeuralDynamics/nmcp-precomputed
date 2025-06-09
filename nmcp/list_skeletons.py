import argparse
import logging

from nmcp import list_skeletons

logging.basicConfig(level=logging.WARNING)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("-o", "--output", help="the output cloud volume location")

    args = parser.parse_args()

    ids = list_skeletons(args.output)

    print(f"{len(ids)} skeletons in {args.output}")

    print(ids)


if __name__ == "__main__":
    main()
