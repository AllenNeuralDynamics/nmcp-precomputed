import tempfile
import shutil
import os

from nmcp import create_from_json_files
from test_utl import verify_precomputed_file


def test_create_from_json():
    temp_dir = tempfile.mkdtemp()
    try:
        json_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "fixtures", "small.json"))

        create_from_json_files([json_file], f"file://{temp_dir}")

        verify_precomputed_file(temp_dir, 40, 63803)
    finally:
        shutil.rmtree(temp_dir)


if __name__ == "__main__":
    test_create_from_json()
