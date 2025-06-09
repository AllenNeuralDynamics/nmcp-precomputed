import json
import logging
from datetime import datetime

from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport

from .precomputed_entry import PrecomputedEntry

logger = logging.getLogger(__name__)

pending_query = gql(
    """
    query QueryPrecomputed {
          pendingPrecomputed {
            id
            skeletonSegmentId
            version
            generatedAt
            reconstructionId
          }
    }
    """
)

update_mutation = gql(
    """
    mutation UpdatePrecomputed($id: String!, $version: Int!, $generatedAt: Date!) {
        updatePrecomputed(id: $id, version: $version, generatedAt: $generatedAt) {
            id
            skeletonSegmentId
            version
            generatedAt
            reconstructionId
        }
    }
    """
)

reconstruction_data_query = gql(
    """
    query ReconstructionData($id: String!) {
        reconstructionData(id: $id)
    }
    """
)


class RemoteDataClient:
    def __init__(self, url: str, auth_key: str):
        transport = RequestsHTTPTransport(
            url=url,
            verify=True,
            retries=3,
            headers={"Content-Type": "application/json", "Authorization": auth_key}
        )

        self._client = Client(transport=transport, fetch_schema_from_transport=False)

    def find_pending(self) -> list:
        pending = list()

        result = self._client.execute(pending_query)

        for precomputed in result["pendingPrecomputed"]:
            pending.append(PrecomputedEntry(**precomputed))

        return pending

    def mark_generated(self, entry_id: str) -> None:
        params = {"id": entry_id, "version": 1, "generatedAt": datetime.now().timestamp() * 1000}
        result = self._client.execute(update_mutation, variable_values=params)

    def mark_failed(self, entry_id: str) -> None:
        params = {"id": entry_id, "version": -1, "generatedAt": datetime.now().timestamp() * 1000}
        result = self._client.execute(update_mutation, variable_values=params)

    def get_reconstruction_data(self, reconstruction_id: str):
        params = {"id": reconstruction_id}

        try:
            result = self._client.execute(reconstruction_data_query, variable_values=params)

            if result and "reconstructionData" in result:
                data = json.loads(result["reconstructionData"])
                if "neurons" in data and len(data["neurons"]) > 0:
                    return data["neurons"][0]
        except Exception as ex:
            logger.error(f"Error getting reconstruction data for {reconstruction_id}", None, ex, True)

        return None
