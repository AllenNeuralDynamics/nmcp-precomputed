import argparse

from .precomputed_worker import main

parser = argparse.ArgumentParser()

parser.add_argument("-u", "--url", help="URL of the GraphQL service")
parser.add_argument("-a", "--authkey", help="authorization header for GraphQL service")
parser.add_argument("-o", "--output", help="the output cloud volume location")

args = parser.parse_args()

main(args.url, args.authkey, args.output)
