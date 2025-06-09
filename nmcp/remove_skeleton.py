import argparse
import logging

from nmcp import remove_skeleton

logging.basicConfig(level=logging.WARNING)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("-o", "--output", help="the output cloud volume location")
    parser.add_argument("-s", "--skeleton", help="the is of the skeleton to remove", type=int)

    args = parser.parse_args()

    remove_skeleton(args.skeleton, args.output)


if __name__ == "__main__":
    main()
