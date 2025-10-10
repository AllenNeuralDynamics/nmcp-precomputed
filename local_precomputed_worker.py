import argparse

from nmcp.precomputed_worker import main

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument("-u", "--url", help="URL of the GraphQL service")
    parser.add_argument("-a", "--authkey", help="authorization header for GraphQL service")
    parser.add_argument("-o", "--output", help="the output cloud volume location")

    args = parser.parse_args()

    main(args.url, args.authkey, args.output)
