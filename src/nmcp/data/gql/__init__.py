from pathlib import Path

from gql import gql


def load_query_document(name: str):
    path = Path(__file__).parent.joinpath(name)

    with open(path, "r") as f:
        return gql(f.read())
