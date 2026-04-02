import logging
from datetime import datetime
from enum import IntEnum

from typing_extensions import List

from gql import Client
from gql.transport.requests import RequestsHTTPTransport

from .gql import load_query_document
from .precomputed_entry import PrecomputedEntry

logger = logging.getLogger(__name__)

PRECOMPUTED_VERSION = 1


class PrecomputedStatus(IntEnum):
    Initialized = 0,
    Pending = 100,
    Passed = 200,
    FailedToLoad = 300,
    FailedToGenerate = 400


class RemoteDataClient:
    def __init__(self, url: str, auth_key: str):
        transport = RequestsHTTPTransport(
            url=url,
            verify=True,
            retries=3,
            headers={"Content-Type": "application/json", "Authorization": auth_key}
        )

        self._client = Client(transport=transport, fetch_schema_from_transport=False)

        self._query_document = load_query_document("precomputed_queries.gql")

    def find_specimen_space_pending(self) -> List[PrecomputedEntry]:
        pending = list()

        result = self._client.execute(self._query_document, operation_name="QuerySpecimenSpacePending")

        for precomputed in result["specimenSpacePendingPrecomputed"]:
            pending.append(PrecomputedEntry(**precomputed))

        return pending

    def get_exported_specimen_space_reconstruction_data(self, reconstruction_id: str):
        try:
            params = {"id": reconstruction_id}

            result = self._client.execute(self._query_document, operation_name="QuerySpecimenSpaceReconstruction",
                                          variable_values=params)

            if not result or "exportedSpecimenReconstruction" not in result:
                return None

            return result["exportedSpecimenReconstruction"]

        except Exception as ex:
            logger.error(f"Error getting specimen reconstruction {reconstruction_id}: {ex}")

        return None

    def _updated_precomputed_entry(self, operation_name: str, entry_id: str, status: PrecomputedStatus):
        params = {"id": entry_id, "status": status, "version": PRECOMPUTED_VERSION,
                  "generatedAt": datetime.now().timestamp() * 1000}
        self._client.execute(self._query_document, operation_name=operation_name, variable_values=params)

    def mark_specimen_generated(self, entry_id: str) -> None:
        self._updated_precomputed_entry("UpdateSpecimenSpacePrecomputed", entry_id, PrecomputedStatus.Passed)

    def mark_specimen_failed_load(self, entry_id: str) -> None:
        self._updated_precomputed_entry("UpdateSpecimenSpacePrecomputed", entry_id, PrecomputedStatus.FailedToLoad)

    def mark_specimen_failed_generate(self, entry_id: str) -> None:
        self._updated_precomputed_entry("UpdateSpecimenSpacePrecomputed", entry_id, PrecomputedStatus.FailedToGenerate)

    def find_atlas_pending(self) -> List[PrecomputedEntry]:
        pending = list()

        result = self._client.execute(self._query_document, operation_name="QueryAtlasSpacePending")

        for precomputed in result["pendingPrecomputed"]:
            pending.append(PrecomputedEntry(**precomputed))

        return pending

    def get_exported_atlas_space_reconstruction_data(self, reconstruction_id: str):
        try:
            params = {"id": reconstruction_id}

            result = self._client.execute(self._query_document, operation_name="QueryAtlasSpaceReconstruction",
                                          variable_values=params)

            if not result or "exportedAtlasReconstruction" not in result:
                return None

            return result["exportedAtlasReconstruction"]

        except Exception as ex:
            logger.error(f"Error getting atlas reconstruction {reconstruction_id}: {ex}")

        return None

    def mark_atlas_generated(self, entry_id: str) -> None:
        self._updated_precomputed_entry("UpdateAtlasSpacePrecomputed", entry_id, PrecomputedStatus.Passed)

    def mark_atlas_failed_load(self, entry_id: str) -> None:
        self._updated_precomputed_entry("UpdateAtlasSpacePrecomputed", entry_id, PrecomputedStatus.FailedToLoad)

    def mark_atlas_failed_generate(self, entry_id: str) -> None:
        self._updated_precomputed_entry("UpdateAtlasSpacePrecomputed", entry_id, PrecomputedStatus.FailedToGenerate)