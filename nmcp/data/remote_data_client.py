import json
from datetime import datetime

from gql import Client, gql
from gql.transport.requests import RequestsHTTPTransport

from .precomputed_entry import PrecomputedEntry

query = gql(
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

mutation = gql(
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
            headers={"Content-Type": "application/json", "Authorization": auth_key},
        )

        self._client = Client(transport=transport, fetch_schema_from_transport=True)

    def find_pending(self) -> list:
        pending = list()

        result = self._client.execute(query)

        for precomputed in result["pendingPrecomputed"]:
            pending.append(PrecomputedEntry(**precomputed))

        return pending

    def mark_generated(self, entry: PrecomputedEntry) -> None:
        params = {"id": entry.id, "version": 1, "generatedAt": datetime.now().timestamp() * 1000}
        result = self._client.execute(mutation, variable_values=params)

    def get_reconstruction_data(self, reconstruction_id: str):
        params = {"id": reconstruction_id}
        result = self._client.execute(reconstruction_data_query, variable_values=params)
        if result and "reconstructionData" in result:
            data = json.loads(result["reconstructionData"])
            if "neurons" in data and len(data["neurons"]) > 0:
                return data["neurons"][0]

        return None
