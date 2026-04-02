import argparse
import logging

from .precomputed import list_skeletons

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("-o", "--output", help="the output cloud volume location")

    args = parser.parse_args()

    locations = ["specimen"]

    for location in locations:
        full_path = f"{args.output}/{location}"
        ids = list_skeletons(full_path)

        logger.info(f"{len(ids)} skeletons in {full_path}")

        logger.info(ids)


if __name__ == "__main__":
    main()
