import argparse

from .service import run

parser = argparse.ArgumentParser()

parser.add_argument("-u", "--url", help="URL of the GraphQL service")
parser.add_argument("-a", "--authkey", help="authorization header for GraphQL service")
parser.add_argument("-o", "--output", required=True, help="the output cloud volume location")

args = parser.parse_args()

run(args.url, args.authkey, args.output)
